"""Ducking: lowers other apps' volume (e.g. Spotify) while a clip plays, then restores it."""
import threading
import time


class Ducker(threading.Thread):
    RELEASE_SECONDS = 0.5

    def __init__(self, get_config, is_busy):
        super().__init__(daemon=True, name="hermetiks-ducker")
        self.get_config, self.is_busy = get_config, is_busy
        self.running = True
        self._ducked = []
        self._last_busy = 0.0

    def _duck(self, cfg):
        from pycaw.pycaw import AudioUtilities
        names = {n.strip().lower() for n in cfg["duck_apps"].split(",") if n.strip()}
        level = cfg["duck_level"] / 100
        for session in AudioUtilities.GetAllSessions():
            try:
                if session.Process and session.Process.name().lower() in names:
                    volume = session.SimpleAudioVolume
                    original = volume.GetMasterVolume()
                    volume.SetMasterVolume(original * level, None)
                    self._ducked.append((volume, original))
            except Exception:  # noqa: BLE001 - a session can vanish at any time
                pass

    def _restore(self):
        for volume, original in self._ducked:
            try:
                volume.SetMasterVolume(original, None)
            except Exception:  # noqa: BLE001
                pass
        self._ducked = []

    def run(self):
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:  # noqa: BLE001
            return
        while self.running:
            try:
                cfg = self.get_config()
                busy = cfg["duck"] and self.is_busy()
                now = time.time()
                if busy:
                    self._last_busy = now
                    if not self._ducked:
                        self._duck(cfg)
                elif self._ducked and now - self._last_busy > self.RELEASE_SECONDS:
                    self._restore()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.05)
        self._restore()

    def stop(self):
        self.running = False
