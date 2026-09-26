"""Visual identity: black, white and greys. BBH Bartle for the wordmark, Rethink Sans for the interface."""
import ctypes
import tkinter as tk
from tkinter import ttk

from ..paths import resource

BG, PANEL, KEY, KEY_HI = "#0a0a0a", "#141414", "#1c1c1c", "#2c2c2c"
LINE, MUTED, TEXT, WHITE, KNOB = "#333333", "#8a8a8a", "#d9d9d9", "#ffffff", "#9a9a9a"

TEXT_FAMILY = "Rethink Sans"

_FONT_FILES = ("BBHBartle-Regular.ttf", "RethinkSans-Regular.ttf", "RethinkSans-Medium.ttf", "RethinkSans-Bold.ttf")
FR_PRIVATE = 0x10


def load_fonts():
    """Register the bundled fonts for this process only (no install, no admin rights)."""
    for name in _FONT_FILES:
        ctypes.windll.gdi32.AddFontResourceExW(resource("fonts", name), FR_PRIVATE, 0)


def font(size=9, bold=False):
    return (TEXT_FAMILY, size, "bold") if bold else (TEXT_FAMILY, size)


def style_ttk(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TCombobox", fieldbackground=KEY, background=KEY, foreground=TEXT, bordercolor=LINE,
                    arrowcolor=TEXT, lightcolor=KEY, darkcolor=KEY, padding=4)
    style.map("TCombobox", fieldbackground=[("readonly", KEY)], foreground=[("readonly", TEXT)])
    root.option_add("*TCombobox*Listbox.background", KEY)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", WHITE)
    root.option_add("*TCombobox*Listbox.selectForeground", BG)
    root.option_add("*TCombobox*Listbox.font", font(9))


def button(parent, text, command, **kw):
    return tk.Button(parent, text=text, command=command, relief="flat", bd=0, bg=KEY, fg=TEXT,
                     activebackground=WHITE, activeforeground=BG, font=font(9), padx=10, pady=4, **kw)


def checkbox(parent, text, variable, command, bg=BG):
    return tk.Checkbutton(parent, text=text, variable=variable, command=command, bg=bg, fg=TEXT,
                          selectcolor=KEY, activebackground=bg, activeforeground=WHITE, font=font(9),
                          bd=0, highlightthickness=0)


def slider(parent, variable, lo, hi, length, command):
    return tk.Scale(parent, from_=lo, to=hi, orient="horizontal", variable=variable, showvalue=False,
                    bg=KNOB, fg=TEXT, troughcolor=KEY_HI, highlightthickness=0, bd=0, sliderrelief="flat",
                    activebackground=WHITE, length=length, sliderlength=16, width=10,
                    command=lambda _v: command())


def caption(parent, text, bg=BG):
    return tk.Label(parent, text=text, bg=bg, fg=MUTED, font=font(8))
