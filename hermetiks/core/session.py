"""Session: the backend controller. Owns audio outputs, loaded clips, hotkeys and ducking.

It has no GUI dependency. It talks to the UI through `events` (a thread-safe queue):
    ("flash", slot)  ("refresh", slot)  ("status", message_key, params)
    ("imported", slot, path, title)  ("captured", target, key)
"""
import os
import queue
import shutil
import threading
import time
import uuid

from . import audio, effects, importer, mixer
from .config import Config, sounds_dir
from . import log
from .ducking import Ducker
from .hotkeys import Hook, RawInput
from .nowplaying import NowPlaying
from .slots import DEFAULT_KEYS, ESCAPE_KEY, NO_KEY, SLOT_IDS


class Session:
    def __init__(self, config=None):
        self.cfg = config or Config()
        self.events = queue.SimpleQueue()
        self.outs = []
        self.cache, self.base, self.env, self._gen = {}, {}, {}, {}
        self.pressed = set()
        self.keymap = {}
        self.capture = None
        self.hook = None
        self.raw = None
        self.ducker = None
        self.nowplaying = None
        self._last_reopen = 0.0
        os.makedirs(sounds_dir(), exist_ok=True)

    # -- lifecycle -------------------------------------------------------------------------
    def start(self):
        self.rebuild_keymap()
        self.load_profile()
        self.raw = RawInput(self.handle_key)
        self.raw.start()
        self.raw.ready.wait(3)
        if not self.raw.ok:  # very unlikely: fall back to a hook that both detects and swallows
            log.info("raw input unavailable, using the keyboard hook")
            self.hook = Hook(self.on_key)
            self.hook.start()
        else:
            self.set_suppress(self.cfg["suppress"])
        self.ducker = Ducker(lambda: self.cfg.data, lambda: any(o.busy for o in self.outs),
                             lambda apps: self.events.put(("status", "duck.no_match", {"apps": apps})))
        self.ducker.start()
        if self.cfg["nowplaying"]:
            try:
                self.set_nowplaying(True)
            except Exception as ex:  # noqa: BLE001
                self.events.put(("status", "np.error", {"detail": str(ex)}))

    def shutdown(self):
        self.set_nowplaying(False)
        if self.raw:
            self.raw.stop()
        if self.hook:
            self.hook.stop()
        if self.ducker:
            self.ducker.stop()
        for o in self.outs:
            o.close()
        self.outs = []

    # -- now playing overlay ------------------------------------------------------------
    def set_nowplaying(self, enabled):
        """Start or stop the local OBS overlay server. Returns its URL, or None when off."""
        if enabled and self.nowplaying is None:
            service = NowPlaying(self.cfg["nowplaying_port"])
            service.start()
            self.nowplaying = service
        elif not enabled and self.nowplaying is not None:
            self.nowplaying.stop()
            self.nowplaying = None
        return self.nowplaying.url if self.nowplaying else None

    # -- keys --------------------------------------------------------------------------------
    def slot_key(self, slot):
        k = self.cfg.slot(slot).get("key")
        return tuple(k) if k else DEFAULT_KEYS[slot]

    def stop_key(self):
        return tuple(self.cfg["stop_key"])

    def rebuild_keymap(self):
        self.keymap = {k: s for s in SLOT_IDS if (k := self.slot_key(s))[0]}

    def start_capture(self, target):
        """The next physical key pressed is assigned to `target` (slot id or "stop")."""
        self.capture = target

    def reset_key(self, slot):
        self.cfg.slot(slot).pop("key", None)
        self.rebuild_keymap()
        self.cfg.save()

    def apply_captured(self, target, key):
        if key == ESCAPE_KEY:
            return
        for s in SLOT_IDS:  # a key can only drive one thing
            if s != target and self.slot_key(s) == key:
                self.cfg.slot(s)["key"] = list(NO_KEY)
        if target == "stop":
            self.cfg["stop_key"] = list(key)
        else:
            if self.stop_key() == key:
                self.cfg["stop_key"] = list(NO_KEY)
            self.cfg.slot(target)["key"] = list(key)
        self.rebuild_keymap()
        self.cfg.save()

    def handle_key(self, key, down):
        """Every physical key event (Raw Input thread): capture, stop key and slot triggers."""
        if self.capture is not None:
            if down:
                target, self.capture = self.capture, None
                self.events.put(("captured", target, key))
            return
        if not self.cfg["active"]:
            return
        if key == self.stop_key():
            if down and key not in self.pressed:
                self.pressed.add(key)
                self.stop_all()
            elif not down:
                self.pressed.discard(key)
            return
        slot = self.keymap.get(key)
        if slot is None:
            return
        if down:
            if key in self.pressed:  # auto-repeat
                return
            self.pressed.add(key)
        else:
            self.pressed.discard(key)
        self.trigger(slot, down)

    def swallow(self, key, down):
        """Keyboard-hook decision: should the game / focused app NOT see this key?"""
        if self.capture is not None:
            return True
        return bool(self.cfg["active"] and self.cfg["suppress"] and (key == self.stop_key() or key in self.keymap))

    def on_key(self, key, down):
        """handle_key + swallow in one call (used when the hook is the only input source)."""
        swallow = self.swallow(key, down)
        self.handle_key(key, down)
        return swallow

    def set_suppress(self, enabled):
        """The low-level hook is installed only while "block keys" is on, so it can never slow the keyboard otherwise."""
        if not (self.raw and self.raw.ok):
            return
        if enabled and self.hook is None:
            self.hook = Hook(self.swallow)
            self.hook.start()
        elif not enabled and self.hook is not None:
            self.hook.stop()
            self.hook = None

    # -- playback ----------------------------------------------------------------------------
    def trigger(self, slot, down=True):
        mode = self.cfg.slot(slot)["mode"]
        outs = list(self.outs)
        if not down:
            if mode == "hold":
                for o in outs:
                    o.stop_slot(slot)
            return
        data = self.cache.get(slot)
        if data is None:
            return
        if not any(getattr(getattr(o, "stream", None), "active", True) for o in outs):
            outs = self._heal_outputs() or outs
        if mode == "loop" and any(o.playing(slot) for o in outs):
            for o in outs:
                o.stop_slot(slot)
            return
        for o in outs:
            o.play(data, slot, mode == "loop")
        self.events.put(("flash", slot))

    def _heal_outputs(self):
        """No live audio stream (device unplugged, resume from sleep, device busy at start): reopen, at most every 2 s."""
        now = time.monotonic()
        if now - self._last_reopen < 2.0:
            return None
        self._last_reopen = now
        opened, errors = self.rebuild_outputs()
        log.info("audio outputs reopened: %s%s", opened, f" errors={errors}" if errors else "")
        return list(self.outs)

    def stop_all(self):
        for o in list(self.outs):
            o.stop()

    def rebuild_outputs(self):
        """(Re)open the main and monitor outputs. Returns (opened_names, errors)."""
        for o in self.outs:
            o.close()
        self.outs = []
        available = {name: (index, wasapi) for name, index, wasapi in mixer.output_devices()}
        main = self.cfg["device"] or mixer.default_device_name()
        wanted = [main]
        if self.cfg["monitor"] and self.cfg["monitor"] != main:
            wanted.append(self.cfg["monitor"])
        opened, errors, outs = [], [], []
        for name in wanted:
            if name in available:
                try:
                    out = mixer.Out(*available[name])
                    out.master = self.cfg["master"] / 100
                    outs.append(out)
                    opened.append(name)
                except Exception as ex:  # noqa: BLE001
                    errors.append(f"{name}: {ex}")
        self.outs = outs
        if errors or not opened:
            log.info("audio outputs: opened=%s errors=%s wanted=%s", opened, errors, wanted)
        return opened, errors

    def apply_master(self):
        for o in self.outs:
            o.master = self.cfg["master"] / 100

    # -- clips -----------------------------------------------------------------------------
    def load_profile(self):
        self.stop_all()
        self.cache.clear(); self.base.clear(); self.env.clear()
        for slot in SLOT_IDS:
            if self.cfg.slot(slot)["file"]:
                self.load_slot_async(slot)

    def load_slot_async(self, slot):
        threading.Thread(target=self._load_slot, args=(slot, self.cfg.profile), daemon=True).start()

    def _load_slot(self, slot, profile):
        s = dict(self.cfg.slot(slot))
        if not os.path.exists(s["file"]):
            self.events.put(("status", "status.missing_file", {}))
            return
        try:
            base = audio.load_audio(s["file"])
            rendered = effects.render(base, s)
        except Exception as ex:  # noqa: BLE001
            self.events.put(("status", "status.read_error", {"file": os.path.basename(s["file"]), "detail": str(ex)}))
            return
        if profile == self.cfg.profile:
            self.base[slot], self.cache[slot], self.env[slot] = base, rendered, audio.envelope(base)
            self.events.put(("refresh", slot))

    def rerender(self, slot):
        """Re-apply effects in a worker thread; a newer request supersedes an older one."""
        base = self.base.get(slot)
        if base is None:
            return
        fx = dict(self.cfg.slot(slot))
        self._gen[slot] = generation = self._gen.get(slot, 0) + 1

        def job():
            out = effects.render(base, fx)
            if self._gen.get(slot) == generation:
                self.cache[slot] = out
        threading.Thread(target=job, daemon=True).start()

    def add_file(self, slot, source_path):
        """Copy a user file into the app's sound folder and assign it. Returns the stored path."""
        dest = os.path.join(sounds_dir(), uuid.uuid4().hex[:8] + os.path.splitext(source_path)[1].lower())
        shutil.copy2(source_path, dest)
        self.assign_file(slot, dest, os.path.splitext(os.path.basename(source_path))[0])
        return dest

    def assign_file(self, slot, path, title):
        s = self.cfg.slot(slot)
        s["file"] = path
        if not s["name"]:
            s["name"] = title[:24]
        self.cfg.save()
        self.load_slot_async(slot)

    def clear_slot(self, slot):
        self.cfg.reset_slot(slot)
        for d in (self.cache, self.base, self.env):
            d.pop(slot, None)
        self.cfg.save()

    def import_url(self, slot, url):
        def job():
            try:
                path, title = importer.fetch_url(url, sounds_dir())
                self.events.put(("imported", slot, path, title))
            except Exception as ex:  # noqa: BLE001
                self.events.put(("status", "status.download_failed", {"detail": str(ex)[:120]}))
        threading.Thread(target=job, daemon=True).start()

    # -- profiles --------------------------------------------------------------------------
    def switch_profile(self, name):
        if name in self.cfg["profiles"]:
            self.cfg["profile"] = name
            self.cfg.save()
            self.rebuild_keymap()
            self.load_profile()
