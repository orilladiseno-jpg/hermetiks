"""Mini overlay for the streamer: a small, click-through panel in the top-right corner of the screen.

Shows the sounds mapped to your keys and lights up the one that plays. Like Discord's overlay it floats above
borderless / windowed games (not above exclusive fullscreen). It is a separate window, so OBS Game Capture does
not include it: it is for you, not your viewers.
"""
import ctypes
import tkinter as tk

from ..core.hotkeys import key_name
from ..core.slots import SLOTS
from . import theme
from .theme import BG, MUTED, TEXT, WHITE, font

IDLE_ALPHA, ACTIVE_ALPHA = 0.55, 0.96
FADE_AFTER_MS, FLASH_MS = 2600, 380
MARGIN = 14
GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x80000, 0x20, 0x80, 0x08000000


class Hud:
    def __init__(self, root, session):
        self.root, self.session = root, session
        self.win = None
        self.rows = {}
        self._fade = None
        self.enabled = False

    # -- public -------------------------------------------------------------------------------------
    def set_enabled(self, enabled):
        self.enabled = enabled
        if enabled:
            self.refresh()
        else:
            self._close()

    def refresh(self):
        if not self.enabled:
            return
        slots = [(vk, label) for vk, label in SLOTS if vk in self.session.cache]
        self._close()
        if not slots:
            return
        win = tk.Toplevel(self.root, bg=BG)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", IDLE_ALPHA)
        body = tk.Frame(win, bg=BG, padx=10, pady=8, highlightthickness=1, highlightbackground="#2a2a2a")
        body.pack()
        tk.Label(body, text="HERMETIKS", bg=BG, fg=MUTED, font=("BBH Bartle", 7)).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.rows = {}
        for i, (vk, _) in enumerate(slots, start=1):
            slot = self.session.cfg.slot(vk)
            name = (slot["name"] or "").strip() or "-"
            key = tk.Label(body, text=key_name(*self.session.slot_key(vk)), bg=BG, fg=WHITE, font=font(8, True), anchor="w", width=6, padx=4)
            label = tk.Label(body, text=name[:20], bg=BG, fg=TEXT, font=font(8), anchor="w", padx=4)
            key.grid(row=i, column=0, sticky="ew")
            label.grid(row=i, column=1, sticky="ew")
            self.rows[vk] = (key, label)
        self.win = win
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        win.geometry(f"{w}x{h}+{win.winfo_screenwidth() - w - MARGIN}+{MARGIN}")
        self._click_through(win)
        win.deiconify()

    def flash(self, slot):
        if not self.win or slot not in self.rows:
            return
        key, label = self.rows[slot]
        for w in (key, label):
            w.config(bg=WHITE, fg=BG)
        self.win.attributes("-alpha", ACTIVE_ALPHA)
        self.root.after(FLASH_MS, lambda: self._unflash(slot))
        if self._fade:
            self.root.after_cancel(self._fade)
        self._fade = self.root.after(FADE_AFTER_MS, self._dim)

    def destroy(self):
        self._close()

    # -- internals ------------------------------------------------------------------------------------
    def _unflash(self, slot):
        if self.win and slot in self.rows:
            key, label = self.rows[slot]
            key.config(bg=BG, fg=WHITE)
            label.config(bg=BG, fg=TEXT)

    def _dim(self):
        self._fade = None
        if self.win:
            self.win.attributes("-alpha", IDLE_ALPHA)

    def _close(self):
        if self._fade:
            self.root.after_cancel(self._fade)
            self._fade = None
        if self.win:
            self.win.destroy()
            self.win = None
        self.rows = {}

    @staticmethod
    def _click_through(win):
        """Mouse clicks go to the game underneath; the panel never takes focus."""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(win.winfo_id()) or win.winfo_id()
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        except Exception:  # noqa: BLE001
            pass
