"""System tray icon (optional; the app works without it)."""
from PIL import Image

from ..paths import resource
from .i18n import t


class Tray:
    def __init__(self, on_show, on_toggle, on_quit, is_active):
        import pystray
        menu = pystray.Menu(
            pystray.MenuItem(lambda item: t("tray.show"), lambda: on_show(), default=True),
            pystray.MenuItem(lambda item: t("tray.active"), lambda: on_toggle(), checked=lambda item: is_active()),
            pystray.MenuItem(lambda item: t("tray.quit"), lambda: on_quit()))
        self.icon = pystray.Icon("hermetiks", Image.open(resource("icon-256.png")), "HERMETIKS Soundboard", menu)
        self.icon.run_detached()

    def stop(self):
        self.icon.stop()
