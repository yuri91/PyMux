#!/usr/bin/env python
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Vte
from gi.repository import GLib
import os
import time
import subprocess
import threading

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

tmux = subprocess.Popen(["tmux","-C"],stdout=subprocess.PIPE,stdin=None)

class UpdateThread(threading.Thread):
    def __init__(self, tmux):
        super(UpdateThread,self).__init__()
        self._stop = threading.Event()
        self.tmux = tmux

    def stop(self):
        self._stop.set()
        self.tmux.wait()

    def handle_begin(self,cmd):
        pass
    def handle_end(self,cmd):
        pass
    def handle_output(self,cmd):
        cmd = b" ".join(cmd.split()[2:])
        out = cmd.decode('unicode_escape').encode()
        t1.feed(out)
    def run(self):
        for l in self.tmux.stdout:
            if self._stop.isSet():
                break
            if l.startswith(b"%begin"):
                self.handle_begin(l)
            elif l.startswith(b"%end"):
                self.handle_end(l)
            elif l.startswith(b"%output"):
                self.handle_output(l)
            else:
                print("unsupported command: ",l)
        tmux.terminate()

    

t = UpdateThread(tmux)
t.start()

Gtk.main()
t.stop()
