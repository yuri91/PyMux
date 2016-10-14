#!/usr/bin/env python
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Vte
from gi.repository import GLib
import os
import time
import pexpect
import threading
import re

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

win = Gtk.Window()
win.connect('delete-event', Gtk.main_quit)
grid = Gtk.Grid()
t1 = new_term()
grid.attach(t1,0,0,1,1)
grid.attach(new_term(),1,0,2,1)
win.add(grid)
win.show_all()

tmux = pexpect.spawn("tmux -CC", timeout=0.5)

def keypressed(widget,event):
    key = event.string.encode()
    if event.keyval == Gdk.KEY_Return:
        key = b"Enter"
    tmux.sendline(b"send-keys "+key)

win.connect('key-press-event', keypressed)

class UpdateThread(threading.Thread):
    def __init__(self, tmux, grid):
        super(UpdateThread,self).__init__()
        self.stop_event = threading.Event()
        self.tmux = tmux
        self.grid = grid

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
    def handle_output(self,cmd):
        r = re.search(rb'%output %([0-9]*) (.*)',cmd)
        out = r.group(2).decode('unicode_escape').encode()
        t1.feed(out)
    def run(self):
        while not self.stop_event.isSet():
            try:
                cmd = self.tmux.readline()
            except:
                pass
            if not cmd.endswith(b"\r\n"):
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
            else:
                print("unsupported command: ",cmd)
        tmux.terminate()

t = UpdateThread(tmux, grid)
t.start()

Gtk.main()
t.stop()
t.join()
