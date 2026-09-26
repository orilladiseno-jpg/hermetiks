"""Frontend (tkinter). `run()` is the application entry point."""
import ctypes
import os
import sys
import tkinter as tk

from ..core.config import Config
from ..core.session import Session
from . import i18n, theme
from .main_window import MainWindow


def run(argv=None):
    argv = argv or []
    for stream in ("stdout", "stderr"):  # windowed builds have no console
        if getattr(sys, stream) is None:
            setattr(sys, stream, open(os.devnull, "w"))
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass
    theme.load_fonts()
    config = Config()
    i18n.set_language(config["language"])
    root = tk.Tk()
    MainWindow(root, Session(config), start_hidden="--min" in argv)
    root.mainloop()
