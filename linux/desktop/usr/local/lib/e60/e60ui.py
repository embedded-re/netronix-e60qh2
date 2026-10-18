"""Shared Tk helpers for the E60QH2 e-ink desktop.

Everything is pure black on white so the EPDC auto mode picks the fast DU
waveform for UI updates.
"""
from pathlib import Path
import tkinter as tk

EPDC = Path('/sys/devices/platform/soc/2000000.bus/20f4000.epdc')
CLEAN_STAMP = Path('/run/e60-clean')
FONT = 'DejaVu Sans'
# How far (px) a finger may slide off a tile and still trigger it on release.
SLACK = 24


def full_refresh(mode='gc16'):
    """Redraw the whole panel to clear ghosting; tell e60-refreshd about it."""
    try:
        (EPDC / 'refresh').write_text(mode)
        CLEAN_STAMP.touch()
    except OSError:
        pass


class Tile(tk.Label):
    """Touch button: inverts on press, acts on release inside the tile."""

    def __init__(self, master, text, command, size=26, **kw):
        super().__init__(master, text=text, font=(FONT, size), bg='white', fg='black',
                         highlightthickness=3, highlightbackground='black',
                         highlightcolor='black', bd=0, **kw)
        self.command = command
        self.bind('<ButtonPress-1>', self._press)
        self.bind('<ButtonRelease-1>', self._release)

    def _press(self, _event):
        self.configure(bg='black', fg='white')

    def _release(self, event):
        self.configure(bg='white', fg='black')
        inside = (-SLACK <= event.x < self.winfo_width() + SLACK and
                  -SLACK <= event.y < self.winfo_height() + SLACK)
        if inside and self.command:
            # Let the un-invert reach the screen before a slow action runs.
            self.after(30, self.command)


def fullscreen(root, title):
    root.title(title)
    root.configure(bg='white', cursor='none')
    root.option_add('*Background', 'white')
    root.option_add('*Foreground', 'black')
    root.option_add('*Font', (FONT, 22))
    # Not -fullscreen: Openbox would stack it above the on-screen keyboard.
    # The Openbox rule for class E60* removes decorations.
    root.geometry(f'{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0')
