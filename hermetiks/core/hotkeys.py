"""Global keyboard hook (WH_KEYBOARD_LL) matching physical keys by scancode.

Scancodes make the numpad work regardless of NumLock, and let any key be assigned.
The hook only compares each key with the configured shortcuts; keystrokes are never stored or sent anywhere.
"""
import ctypes
import threading
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, wintypes.DWORD]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]

WH_KEYBOARD_LL = 13
WM_KEYDOWN, WM_SYSKEYDOWN, WM_QUIT = 0x100, 0x104, 0x12

# Short, language-neutral names for the numpad (Windows would return long localized ones).
NUMPAD_NAMES = {(0x52, 0): "Num 0", (0x4F, 0): "Num 1", (0x50, 0): "Num 2", (0x51, 0): "Num 3",
                (0x4B, 0): "Num 4", (0x4C, 0): "Num 5", (0x4D, 0): "Num 6", (0x47, 0): "Num 7",
                (0x48, 0): "Num 8", (0x49, 0): "Num 9", (0x35, 1): "Num /", (0x37, 0): "Num *",
                (0x4A, 0): "Num -", (0x4E, 0): "Num +", (0x53, 0): "Num ."}


def key_name(scancode, extended):
    if not scancode:
        return "-"
    if (scancode, extended) in NUMPAD_NAMES:
        return NUMPAD_NAMES[(scancode, extended)]
    buf = ctypes.create_unicode_buffer(64)
    user32.GetKeyNameTextW((scancode << 16) | (extended << 24), buf, 64)
    return (buf.value or f"#{scancode}").title()


class Hook(threading.Thread):
    """handler(key, down) -> True to swallow the key. `key` is (scancode, extended)."""

    def __init__(self, handler):
        super().__init__(daemon=True, name="hermetiks-hook")
        self.handler = handler
        self._thread_id = None
        self._proc = HOOKPROC(self._callback)

    def _callback(self, code, wparam, lparam):
        if code >= 0:
            info = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            try:
                if self.handler((info.scanCode, info.flags & 1), wparam in (WM_KEYDOWN, WM_SYSKEYDOWN)):
                    return 1
            except Exception:  # noqa: BLE001 - never let an error break the user's keyboard
                pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    def run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        handle = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.UnhookWindowsHookEx(handle)

    def stop(self):
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
