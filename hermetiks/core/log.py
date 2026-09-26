"""Small local log (%APPDATA%/Hermetiks/hermetiks.log) for diagnosing crashes. Never contains key presses or audio."""
import logging
import logging.handlers
import os
import sys
import threading

from .config import data_dir

_logger = logging.getLogger("hermetiks")


def setup():
    if _logger.handlers:
        return _logger
    _logger.setLevel(logging.INFO)
    try:
        os.makedirs(data_dir(), exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(os.path.join(data_dir(), "hermetiks.log"), maxBytes=200_000,
                                                       backupCount=1, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        _logger.addHandler(handler)
    except OSError:
        _logger.addHandler(logging.NullHandler())
    sys.excepthook = lambda *exc: _logger.error("uncaught exception", exc_info=exc)
    threading.excepthook = lambda a: _logger.error("thread %s crashed", a.thread.name if a.thread else "?",
                                                   exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
    return _logger


def info(msg, *args):
    _logger.info(msg, *args)


def exception(msg, *args):
    _logger.error(msg, *args, exc_info=True)
