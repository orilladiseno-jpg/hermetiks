"""Frontend (tkinter). `run()` is the application entry point."""
import ctypes
import os
import sys
import tkinter as tk

from .. import __version__
from ..core import log
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
    log.setup()
    log.info("start v%s argv=%s", __version__, argv)
    theme.load_fonts()
    config = Config()
    i18n.set_language(config["language"])
    root = tk.Tk()
    root.report_callback_exception = lambda *exc: log.exception("tk callback error")
    MainWindow(root, Session(config), start_hidden="--min" in argv)
    root.mainloop()
    log.info("mainloop ended")
