"""Locate bundled files. Works from source and from a PyInstaller build alike."""
import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def resource(*parts):
    return os.path.join(PACKAGE_DIR, "resources", *parts)


def locale_dir():
    return os.path.join(PACKAGE_DIR, "ui", "locales")
