#!/usr/bin/env python
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Vte
from gi.repository import GLib
import os
import time
import subprocess
from threading import Thread

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

def handle():
    tmux = subprocess.Popen(["tmux","-C"],stdout=subprocess.PIPE,stdin=None)
    for l in tmux.stdout:
        if l.startswith(b"%begin"):
            pass
        elif l.startswith(b"%end"):
            pass
        elif l.startswith(b"%output"):
            cmd = b" ".join(l.split()[2:])
            out = cmd.decode('unicode_escape').encode()
            t1.feed(out)
            print("out: ",l)
        else:
            print("unsupported command: ",l)

    

t = Thread(target=handle)
t.start()

Gtk.main()
