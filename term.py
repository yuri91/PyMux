#!/usr/bin/env python
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Vte
from gi.repository import GLib
from gi.repository import GObject
import os
import time
import pexpect
import threading
import re

import re
from enum import Enum

def new_term():
    terminal = Vte.Terminal()
    terminal.spawn_sync(
        Vte.PtyFlags.DEFAULT,
        os.environ['HOME'],
        [],
        [],
        GLib.SpawnFlags.DO_NOT_REAP_CHILD,
        None,
        None,
    )
    terminal.set_vexpand(True)
    terminal.set_hexpand(True)
    return terminal

class LAYOUT_TYPE(Enum):
    NONE = 0
    TOP_BOTTOM = 1
    LEFT_RIGHT = 2

class Layout:
    def __init__(self, parent, sx, sy, xoff, yoff):
        self.parent = parent

        self.sx=sx
        self.sy=sy
        self.xoff=xoff
        self.yoff=yoff

        self.type = LAYOUT_TYPE.NONE
        self.id = -1
        self.children = []
 
        self.widget = None

    def set_type(self,type):
        self.type = type
        if type == LAYOUT_TYPE.TOP_BOTTOM:
            self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        elif type == LAYOUT_TYPE.LEFT_RIGHT:
            self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        else:
            self.widget = new_term()
            self.widget.panel_id = self.id
        if self.parent != None:
            self.parent.widget.pack_start(self.widget,True,True,0)

    def get(self, ID):
        if self.id == ID:
            return self.widget
        for c in self.children:
            res = c.get(ID)
            if res != None:
                return res
        return None

    def __repr__(self):
        if self.type == LAYOUT_TYPE.NONE:
            last = ","+str(self.id)
        else:
            brackets = "[]" if self.type == LAYOUT_TYPE.TOP_BOTTOM else "{}"
            last = brackets[0]
            first = True
            for c in self.children:
                if not first:
                    last += ","
                first = False
                last += repr(c)
            last += brackets[1]
        return "{}x{},{},{}{}".format(self.sx,self.sy,self.xoff,self.yoff, last)

def parse_layout(parent, layout, cur):
    r = re.search("^(\d+)x(\d+),(\d+),(\d+)", layout[cur:])
    if not r:
        return None, cur
    cur += len(r.group(0))
    l = Layout(parent, *map(int,r.groups()))
    if layout[cur] == ",":
        r = re.search("^,(\d+)",layout[cur:])
        if r == None:
            return None, cur
        cur += len(r.group(0))
        l.id = int(r.group(1))
        l.set_type(LAYOUT_TYPE.NONE)
    if cur == len(layout) or layout[cur] in ',}]': return (l,cur)
    if layout[cur] == "{":
        l.set_type(LAYOUT_TYPE.LEFT_RIGHT)
    elif layout[cur] == "[":
        l.set_type(LAYOUT_TYPE.TOP_BOTTOM)
    else:
        return None, cur
    while True:
        cur += 1
        child,cur = parse_layout(l, layout, cur)
        if child == None:
            return None, cur
        l.children.append(child)
        if layout[cur] != ",": break

    if l.type == LAYOUT_TYPE.LEFT_RIGHT:
        if layout[cur] != "}": return None, cur
    elif l.type == LAYOUT_TYPE.TOP_BOTTOM:
        if layout[cur] != "]": return None, cur

    cur +=1

    return (l,cur)

class UpdateThread(threading.Thread):
    def __init__(self, tmux, widget):
        super(UpdateThread,self).__init__()
        self.stop_event = threading.Event()
        self.tmux = tmux
        self.widget=widget
        self.layout = None

    def stop(self):
        self.stop_event.set()

    def handle_begin(self,cmd):
        print("begin: ",cmd)
    def handle_end(self,cmd):
        print("end: ",cmd)
    def handle_exit(self,cmd):
        print("exit: ",cmd)
        self.stop_event.set()
    def handle_window_add(self,cmd):
        print("window-add: ",cmd)
    def handle_layout_change(self,cmd):
        print("layout_change: ",cmd)
        cmd = cmd.split()[2].partition(b",")[2]
        l,n = parse_layout(None,cmd.decode(),0)
        print(l)
        def update_widget(widget,new,old):
            if old:
                widget.remove(old)
            widget.add(new)
            widget.show_all()
        oldchild = None if not self.layout else self.layout.widget
        self.layout = l
        GObject.idle_add(update_widget,self.widget,l.widget,oldchild)
    def handle_output(self,cmd):
        r = re.search(rb'%output %([0-9]*) (.*)',cmd)
        out = r.group(2).decode('unicode_escape').encode()
        print(out)
        panel = int(r.group(1))
        t = self.layout.get(panel)
        t.feed(out)
    def run(self):
        while not self.stop_event.isSet():
            try:
                cmd = self.tmux.readline()
            except:
                continue
            if not cmd.endswith(b"\r\n"):
                print(cmd)
                print("tmux died, exiting now.")
                exit(-1)

            cmd = cmd.strip()
            if cmd.startswith(b"%begin"):
                self.handle_begin(cmd)
            elif cmd.startswith(b"%end"):
                self.handle_end(cmd)
            elif cmd.startswith(b"%output"):
                self.handle_output(cmd)
            elif cmd.startswith(b"%exit"):
                self.handle_exit(cmd)
            elif cmd.startswith(b"%window-add"):
                self.handle_window_add(cmd)
            elif cmd.startswith(b"%layout-change"):
                self.handle_layout_change(cmd)
            else:
                print("unsupported command: ",cmd)
        tmux.terminate()

win = Gtk.Window()
win.connect('delete-event', Gtk.main_quit)
win.show_all()

tmux = pexpect.spawn("tmux -CC attach", timeout=0.5)

def keypressed(widget,event):
    vte = widget.get_focus()
    if not vte: return
    key = event.string.encode()
    if event.keyval == Gdk.KEY_Return:
        key = b"Enter"
    tmux.sendline(b"send-keys -t %" + str(vte.panel_id).encode()+ b" " + key)

win.connect('key-press-event', keypressed)

t = UpdateThread(tmux, win)
t.start()

Gtk.main()
t.stop()
t.join()
