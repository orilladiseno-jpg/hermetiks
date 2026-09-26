"""Keep HERMETIKS responsive in the background.

Windows 11 can put minimized / background apps in "efficiency mode" (slower threads, coarser timers), which delays
hotkeys and audio. We opt out of that throttling and ask for a slightly higher priority. Best effort: never raises.
"""
import ctypes
from ctypes import wintypes

PROCESS_POWER_THROTTLING = 4
THROTTLING_EXECUTION_SPEED, THROTTLING_IGNORE_TIMER_RESOLUTION = 0x1, 0x4
ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000


class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]


def keep_responsive():
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        process = kernel32.GetCurrentProcess()
        state = PROCESS_POWER_THROTTLING_STATE(1, THROTTLING_EXECUTION_SPEED | THROTTLING_IGNORE_TIMER_RESOLUTION, 0)
        kernel32.SetProcessInformation(process, PROCESS_POWER_THROTTLING, ctypes.byref(state), ctypes.sizeof(state))
        kernel32.SetPriorityClass(process, ABOVE_NORMAL_PRIORITY_CLASS)
        ctypes.WinDLL("winmm").timeBeginPeriod(1)
        return True
    except Exception:  # noqa: BLE001
        return False
