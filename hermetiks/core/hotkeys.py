"""Global keyboard input, matching physical keys by scancode.

* RawInput  detects the keys (WM_INPUT with RIDEV_INPUTSINK). It keeps working while the window is minimized, in the
            tray or behind a game, and Windows never drops it for being slow (unlike a low-level hook).
* Hook      (WH_KEYBOARD_LL) is only installed while "block keys for the game" is on, purely to swallow keys.

Scancodes make the numpad work regardless of NumLock, and let any key be assigned.
Keys are only compared with the configured shortcuts; keystrokes are never stored or sent anywhere.
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


# ---- Raw Input ----------------------------------------------------------------------------------------------
WM_INPUT, RIM_TYPEKEYBOARD, RID_INPUT = 0x00FF, 1, 0x10000003
RIDEV_INPUTSINK, RI_KEY_BREAK, RI_KEY_E0 = 0x00000100, 0x01, 0x02
HWND_MESSAGE = ctypes.c_void_p(-3)
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HANDLE), ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HANDLE), ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT), ("dwFlags", wintypes.DWORD),
                ("hwndTarget", wintypes.HWND)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD), ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [("MakeCode", wintypes.USHORT), ("Flags", wintypes.USHORT), ("Reserved", wintypes.USHORT),
                ("VKey", wintypes.USHORT), ("Message", wintypes.UINT), ("ExtraInformation", wintypes.ULONG)]


class RAWINPUT(ctypes.Structure):
    _fields_ = [("header", RAWINPUTHEADER), ("keyboard", RAWKEYBOARD), ("pad", ctypes.c_ubyte * 32)]


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
user32.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPVOID, ctypes.POINTER(wintypes.UINT), wintypes.UINT]


class RawInput(threading.Thread):
    """handler(key, down) for every physical key press/release, from a hidden message-only window."""

    def __init__(self, handler):
        super().__init__(daemon=True, name="hermetiks-rawinput")
        self.handler = handler
        self.ready = threading.Event()
        self.ok = False
        self._thread_id = None
        self._wndproc = WNDPROC(self._proc)

    def _proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            try:
                self._read(lparam)
            except Exception:  # noqa: BLE001
                pass
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _read(self, handle):
        raw = RAWINPUT()
        size = wintypes.UINT(ctypes.sizeof(raw))
        got = user32.GetRawInputData(handle, RID_INPUT, ctypes.byref(raw), ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
        if got == 0xFFFFFFFF or raw.header.dwType != RIM_TYPEKEYBOARD:
            return
        kb = raw.keyboard
        if kb.MakeCode in (0, 0xFF):  # fake keys Windows injects around NumLock / Shift
            return
        self.handler((kb.MakeCode, 1 if kb.Flags & RI_KEY_E0 else 0), not (kb.Flags & RI_KEY_BREAK))

    def run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        instance = kernel32.GetModuleHandleW(None)
        cls = WNDCLASSW()
        cls.lpfnWndProc, cls.hInstance, cls.lpszClassName = self._wndproc, instance, "HermetiksRawInput"
        user32.RegisterClassW(ctypes.byref(cls))
        hwnd = user32.CreateWindowExW(0, "HermetiksRawInput", "HermetiksRawInput", 0, 0, 0, 0, 0, HWND_MESSAGE, None, instance, None)
        dev = RAWINPUTDEVICE(1, 6, RIDEV_INPUTSINK, hwnd)  # generic desktop / keyboard, also when not focused
        self.ok = bool(hwnd) and bool(user32.RegisterRawInputDevices(ctypes.byref(dev), 1, ctypes.sizeof(dev)))
        self.ready.set()
        if not self.ok:
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self):
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
