"""Single instance: a second copy would double every sound. Instead, bring the running one to the front."""
import ctypes

ERROR_ALREADY_EXISTS = 183
SW_SHOW, SW_RESTORE = 5, 9
_handle = None  # keep the mutex alive for the life of the process


def acquire(name="Local\\HermetiksSoundboard"):
    """True if this is the only instance."""
    global _handle
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    _handle = kernel32.CreateMutexW(None, False, name)
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def focus_existing(title="HERMETIKS Soundboard"):
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = user32.FindWindowW(None, title)
    if hwnd:
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.ShowWindow(hwnd, SW_SHOW)
        user32.SetForegroundWindow(hwnd)
    return bool(hwnd)
