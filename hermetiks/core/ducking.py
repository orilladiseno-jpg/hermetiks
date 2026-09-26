"""Ducking: smoothly lowers other apps' volume (e.g. Spotify) while a clip plays, then brings it back.

The fade uses a smoothstep curve: fast but never a hard cut (about 0.16 s down, 0.5 s up).
The original volumes are written to disk while ducked, so if HERMETIKS is closed or crashes mid-duck the
next start puts them back.
"""
import json
import os
import re
import threading
import time

from . import log
from .config import data_dir

ATTACK = 0.16   # seconds to reach the ducked level
RELEASE = 0.50  # seconds to come back
HOLD = 0.25     # keep ducked this long after the last clip so quick consecutive clips don't pump the music
FRAME = 1 / 60


def normalize_apps(text):
    """"/spotify.exe/", "Spotify.exe", "C:\\Apps\\Spotify.exe", 'spotify' -> ["spotify"]. Tolerant on purpose."""
    tokens = []
    for raw in re.split(r"[,;\n]+", text or ""):
        parts = [p for p in raw.strip().strip("\"' ").replace("\\", "/").split("/") if p.strip()]
        if not parts:
            continue
        token = parts[-1].strip().lower()
        token = token[:-4] if token.endswith(".exe") else token
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def app_matches(process_name, tokens):
    base = process_name.lower()
    base = base[:-4] if base.endswith(".exe") else base
    return any(t == base or (len(t) >= 3 and t in base) for t in tokens)


def running_audio_apps():
    """Names of the apps that currently have an audio session on any output device (for the picker)."""
    result = []

    def work():
        try:
            import comtypes
            comtypes.CoInitialize()
            for _, s in iter_sessions():
                try:
                    name = s.Process.name() if s.Process else ""
                except Exception:  # noqa: BLE001
                    name = ""
                if name and name not in result and name.lower() not in ("svchost.exe", "audiodg.exe"):
                    result.append(name)
        except Exception:  # noqa: BLE001
            pass
    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(3)
    return sorted(result, key=str.lower)


def ease(p):
    return p * p * (3 - 2 * p)


class DuckRamp:
    """Pure fade state (0 = normal, 1 = fully ducked). Unit-tested without any audio."""

    def __init__(self, attack=ATTACK, release=RELEASE, hold=HOLD):
        self.attack, self.release, self.hold = attack, release, hold
        self.p = 0.0
        self._quiet = hold  # time since a clip last played

    def step(self, dt, want):
        self._quiet = 0.0 if want else self._quiet + dt
        if want or self._quiet < self.hold:
            self.p = min(1.0, self.p + dt / self.attack)
        else:
            self.p = max(0.0, self.p - dt / self.release)
        return self.p

    def factor(self, level):
        """Volume multiplier for a ducked level in 0..1 (1 = no ducking)."""
        return 1 - (1 - level) * ease(self.p)


class _Tracked:
    def __init__(self, key, name, volume, original):
        self.key, self.name, self.volume, self.original = key, name, volume, original


def iter_sessions():
    """(device_id, AudioSession) for the audio sessions of EVERY active output device.

    pycaw's GetAllSessions() only looks at the default device; with VB-CABLE the music often plays on another one.
    """
    import comtypes
    from comtypes import CLSCTX_ALL
    from pycaw.api.audiopolicy import IAudioSessionControl2, IAudioSessionManager2
    from pycaw.api.mmdeviceapi import IMMDeviceEnumerator
    from pycaw.constants import CLSID_MMDeviceEnumerator
    from pycaw.utils import AudioSession
    enum = comtypes.CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER)
    devices = enum.EnumAudioEndpoints(0, 1)  # eRender, DEVICE_STATE_ACTIVE
    for i in range(devices.GetCount()):
        try:
            device = devices.Item(i)
            manager = device.Activate(IAudioSessionManager2._iid_, CLSCTX_ALL, None).QueryInterface(IAudioSessionManager2)
            sessions = manager.GetSessionEnumerator()
            for j in range(sessions.GetCount()):
                yield device.GetId(), AudioSession(sessions.GetSession(j).QueryInterface(IAudioSessionControl2))
        except Exception:  # noqa: BLE001 - a device can disappear while we look
            continue


def _state_path():
    return os.path.join(data_dir(), "duck_state.json")


class Ducker(threading.Thread):
    def __init__(self, get_config, is_busy, on_no_match=None):
        super().__init__(daemon=True, name="hermetiks-ducker")
        self.get_config, self.is_busy, self.on_no_match = get_config, is_busy, on_no_match
        self._warned = 0.0
        self.running = True
        self.ramp = DuckRamp()
        self._tracked = {}
        self._last_scan = 0.0
        self._logged = None

    # -- Windows audio sessions -------------------------------------------------------------
    def _scan(self, tokens):
        names = tokens
        for device_id, s in iter_sessions():
            try:
                if not (s.Process and app_matches(s.Process.name(), tokens)):
                    continue
                key = f"{device_id}|{getattr(s, 'InstanceIdentifier', None) or s.Process.pid}"
                if key not in self._tracked:
                    volume = s.SimpleAudioVolume
                    self._tracked[key] = _Tracked(key, s.Process.name().lower(), volume, volume.GetMasterVolume())
            except Exception:  # noqa: BLE001 - sessions can vanish at any time
                pass
        count = len(self._tracked)
        if count != self._logged:
            self._logged = count
            log.info("duck: %d audio session(s) matched %s", count, sorted(names))
        if count == 0 and self.on_no_match and time.monotonic() - self._warned > 8:
            self._warned = time.monotonic()
            self.on_no_match(", ".join(tokens))
        self._save_state()

    def _apply(self, factor):
        for t in list(self._tracked.values()):
            try:
                t.volume.SetMasterVolume(max(0.0, min(1.0, t.original * factor)), None)
            except Exception:  # noqa: BLE001
                self._tracked.pop(t.key, None)

    def _restore(self):
        self._apply(1.0)
        self._tracked = {}
        self._logged = None
        try:
            os.remove(_state_path())
        except OSError:
            pass

    def _save_state(self):
        try:
            with open(_state_path(), "w", encoding="utf-8") as f:
                json.dump({t.name: t.original for t in self._tracked.values()}, f)
        except OSError:
            pass

    def _recover(self):
        """A previous run was closed while ducked: put those apps' volumes back."""
        try:
            with open(_state_path(), encoding="utf-8") as f:
                saved = json.load(f)
        except (OSError, ValueError):
            return
        try:
            for _, s in iter_sessions():
                if s.Process and s.Process.name().lower() in saved:
                    s.SimpleAudioVolume.SetMasterVolume(float(saved[s.Process.name().lower()]), None)
            log.info("duck: restored volumes left over from a previous run")
        except Exception:  # noqa: BLE001
            pass
        try:
            os.remove(_state_path())
        except OSError:
            pass

    # -- loop ---------------------------------------------------------------------------------
    def run(self):
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:  # noqa: BLE001
            log.exception("duck: COM init failed")
            return
        self._recover()
        last = time.perf_counter()
        while self.running:
            try:
                cfg = self.get_config()
                now = time.perf_counter()
                dt, last = now - last, now
                want = bool(cfg["duck"]) and self.is_busy()
                moving = want or self.ramp.p > 0 or self.ramp._quiet < self.ramp.hold
                if moving:
                    if not self._tracked or now - self._last_scan > 0.5:
                        self._scan(normalize_apps(cfg["duck_apps"]))
                        self._last_scan = now
                    self.ramp.step(dt, want)
                    self._apply(self.ramp.factor(cfg["duck_level"] / 100))
                    if self.ramp.p == 0 and not want:
                        self._restore()
            except Exception:  # noqa: BLE001
                log.exception("duck: loop error")
            time.sleep(FRAME if (self.ramp.p > 0 or self.is_busy()) else 0.05)
        self._restore()

    def stop(self):
        self.running = False
