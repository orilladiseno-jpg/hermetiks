"""About / legal dialog."""
import os
import tkinter as tk
import webbrowser

from .. import COLLECTIVE, COMPANY, COPYRIGHT, WEBSITE, __version__
from ..paths import PACKAGE_DIR, resource
from . import theme
from .i18n import t

THIRD_PARTY = [
    ("Python", "PSF-2.0"), ("Tcl/Tk", "Tcl/Tk license"), ("NumPy", "BSD-3-Clause"),
    ("sounddevice / PortAudio", "MIT"), ("SoundFile / libsndfile", "BSD-3-Clause / LGPL-2.1"),
    ("PyAV / FFmpeg", "BSD-3-Clause / LGPL-3.0-or-later"), ("Pillow", "MIT-CMU (HPND)"),
    ("pystray", "LGPL-3.0"), ("pycaw / comtypes", "MIT"), ("yt-dlp", "Unlicense"),
    ("BBH Bartle (font)", "SIL OFL 1.1"), ("Rethink Sans (font)", "SIL OFL 1.1"),
]


def _license_text():
    for path in (resource("LICENSE.txt"), os.path.join(os.path.dirname(PACKAGE_DIR), "LICENSE")):
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except OSError:
            continue
    return "MIT License"


class About(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent, bg=theme.BG, padx=28, pady=22)
        self.title(t("about.title"))
        self.resizable(False, False)
        self.transient(parent)
        text = tk.Text(self, width=64, height=25, bg=theme.PANEL, fg=theme.TEXT, relief="flat", wrap="word",
                       font=theme.font(9), padx=16, pady=12, highlightthickness=0, cursor="arrow", spacing3=4)
        text.tag_configure("h", font=theme.font(10, True), foreground=theme.WHITE, spacing1=8)
        text.tag_configure("m", foreground=theme.MUTED)

        def add(s, tag=None):
            text.insert("end", s + "\n", tag)

        add(f"HERMETIKS Soundboard   {t('about.version', version=__version__)}", "h")
        add(t("about.credit"))
        add(COPYRIGHT, "m")
        add("")
        add(t("about.opensource"))
        add(t("about.warranty"), "m")
        add(t("about.privacy_title"), "h")
        add(t("about.privacy"))
        add(t("about.content_title"), "h")
        add(t("about.content"))
        add(t("about.third"), "h")
        for name, lic in THIRD_PARTY:
            add(f"  {name} - {lic}", "m")
        text.config(state="disabled")
        text.pack()
        bar = tk.Frame(self, bg=theme.BG)
        bar.pack(fill="x", pady=(14, 0))
        theme.button(bar, t("about.license_btn"), self._show_license).pack(side="left")
        theme.button(bar, t("about.website_btn"), lambda: webbrowser.open(WEBSITE)).pack(side="left", padx=8)
        theme.button(bar, t("about.close"), self.destroy).pack(side="right")
        self.grab_set()

    def _show_license(self):
        win = tk.Toplevel(self, bg=theme.BG, padx=20, pady=16)
        win.title("MIT License")
        box = tk.Text(win, width=80, height=22, bg=theme.PANEL, fg=theme.TEXT, relief="flat", wrap="word",
                      font=theme.font(9), padx=14, pady=10, highlightthickness=0)
        box.insert("1.0", _license_text())
        box.config(state="disabled")
        box.pack()
        theme.button(win, t("about.close"), win.destroy).pack(pady=(12, 0), anchor="e")
