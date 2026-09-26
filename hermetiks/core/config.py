"""Persistent settings: %APPDATA%/Hermetiks/config.json (profiles, slots, options)."""
import json
import os

from .effects import DEFAULT_FX
from .slots import DEFAULT_STOP

SCHEMA_VERSION = 3


def data_dir():
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Hermetiks")


def sounds_dir():
    return os.path.join(data_dir(), "sounds")


def default_path():
    return os.path.join(data_dir(), "config.json")


DEFAULTS = dict(version=SCHEMA_VERSION, language="en", device="", monitor="", master=100, suppress=False,
                active=True, close_tray=False, startup=False, hud=True, duck=True, duck_level=30,
                duck_apps="spotify.exe", nowplaying=True, nowplaying_port=8765,
                stop_key=list(DEFAULT_STOP), profile="Main", profiles={})


class Config:
    def __init__(self, path=None):
        self.path = path or default_path()
        self.data = self._load()

    # -- persistence ---------------------------------------------------------------------
    def _load(self):
        data = json.loads(json.dumps(DEFAULTS))
        saved_version = SCHEMA_VERSION
        try:
            with open(self.path, encoding="utf-8") as f:
                saved = json.load(f)
            saved_version = saved.get("version", 1)
            data.update(saved)
        except (OSError, ValueError):
            pass
        if saved_version < 3:  # ducking was off and hidden before: turn on the new smooth duck once
            data["duck"], data["hud"], data["nowplaying"] = True, True, True
            if data.get("duck_level") == 25:
                data["duck_level"] = 30
        return self._migrate(data)

    @staticmethod
    def _migrate(data):
        if "slots" in data:  # v1: a single flat set of slots
            data["profiles"].setdefault("Main", {"slots": data.pop("slots")})
            data["profile"] = "Main"
        if data.get("profile") == "Principal":  # early builds used a Spanish default name
            data["profiles"].setdefault("Main", data["profiles"].pop("Principal", {"slots": {}}))
            data["profile"] = "Main"
        if not data["profiles"]:
            data["profiles"][data["profile"]] = {"slots": {}}
        if data["profile"] not in data["profiles"]:
            data["profile"] = next(iter(data["profiles"]))
        data["version"] = SCHEMA_VERSION
        return data

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=1, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError:
            pass

    # -- access ----------------------------------------------------------------------------
    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    @property
    def profile(self):
        return self.data["profile"]

    @property
    def profile_names(self):
        return list(self.data["profiles"])

    def slot(self, slot_id):
        """The mutable settings dict of a slot in the active profile (defaults filled in)."""
        slots = self.data["profiles"][self.profile]["slots"]
        s = slots.setdefault(str(slot_id), {})
        s.setdefault("name", "")
        s.setdefault("file", "")
        s.setdefault("mode", "normal")
        for k, v in DEFAULT_FX.items():
            s.setdefault(k, v)
        return s

    def reset_slot(self, slot_id):
        """Clear a slot's audio and effects but keep its assigned key."""
        slots = self.data["profiles"][self.profile]["slots"]
        key = slots.get(str(slot_id), {}).get("key")
        slots.pop(str(slot_id), None)
        if key:
            self.slot(slot_id)["key"] = key

    # -- profiles --------------------------------------------------------------------------
    def add_profile(self, name):
        name = name.strip()
        if not name or name in self.data["profiles"]:
            return False
        self.data["profiles"][name] = {"slots": {}}
        return True

    def rename_profile(self, name):
        name = name.strip()
        if not name or name in self.data["profiles"]:
            return False
        self.data["profiles"] = {(name if k == self.profile else k): v for k, v in self.data["profiles"].items()}
        self.data["profile"] = name
        return True

    def delete_profile(self):
        if len(self.data["profiles"]) < 2:
            return False
        del self.data["profiles"][self.profile]
        self.data["profile"] = next(iter(self.data["profiles"]))
        return True
