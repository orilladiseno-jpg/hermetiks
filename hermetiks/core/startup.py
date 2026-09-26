"""Start with Windows (per-user Run key; no admin rights needed)."""
import os
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = "Hermetiks"


def command_line():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --min'
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    return f'"{pythonw}" -m hermetiks --min'


def is_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, VALUE)
            return True
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def set_enabled(enabled):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    try:
        if enabled:
            winreg.SetValueEx(key, VALUE, 0, winreg.REG_SZ, command_line())
        else:
            try:
                winreg.DeleteValue(key, VALUE)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)
