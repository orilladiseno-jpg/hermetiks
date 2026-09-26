import json

from hermetiks.core.config import Config, SCHEMA_VERSION, default_path


def write(data):
    import os
    os.makedirs(os.path.dirname(default_path()), exist_ok=True)
    with open(default_path(), "w", encoding="utf-8") as f:
        json.dump(data, f)


def test_defaults_when_no_file():
    cfg = Config()
    assert cfg["language"] == "en"
    assert cfg.profile == "Main" and cfg.profile_names == ["Main"]


def test_roundtrip():
    cfg = Config()
    cfg.slot(97)["name"] = "hello"
    cfg.save()
    assert Config().slot(97)["name"] == "hello"


def test_migrates_v1_flat_slots():
    write({"slots": {"97": {"name": "old", "file": "x.wav"}}})
    cfg = Config()
    assert cfg.slot(97)["name"] == "old"
    assert cfg["version"] == SCHEMA_VERSION and "slots" not in cfg.data


def test_migrates_early_spanish_default_profile_name():
    write({"profile": "Principal", "profiles": {"Principal": {"slots": {"96": {"name": "a"}}}}})
    cfg = Config()
    assert cfg.profile == "Main" and cfg.slot(96)["name"] == "a"


def test_corrupt_file_falls_back_to_defaults():
    write({})
    with open(default_path(), "w") as f:
        f.write("{not json")
    assert Config().profile == "Main"


def test_profile_lifecycle():
    cfg = Config()
    assert cfg.add_profile("Rematch") and not cfg.add_profile("Rematch") and not cfg.add_profile("  ")
    cfg["profile"] = "Rematch"
    assert cfg.rename_profile("Radio") and cfg.profile == "Radio"
    assert cfg.delete_profile() and cfg.profile == "Main"
    assert not cfg.delete_profile()  # never delete the last profile


def test_reset_slot_keeps_assigned_key():
    cfg = Config()
    s = cfg.slot(98)
    s["name"], s["key"] = "x", [30, 0]
    cfg.reset_slot(98)
    assert cfg.slot(98)["name"] == "" and cfg.slot(98)["key"] == [30, 0]


def test_new_installs_get_the_streamer_friendly_defaults():
    cfg = Config()
    assert cfg["duck"] is True and cfg["hud"] is True and cfg["nowplaying"] is True
    assert cfg["duck_level"] == 30 and cfg["nowplaying_port"] == 8765


def test_old_builds_get_smooth_duck_switched_on_once():
    write({"version": 2, "duck": False, "duck_level": 25, "profiles": {"Main": {"slots": {}}}, "profile": "Main"})
    cfg = Config()
    assert cfg["duck"] is True and cfg["duck_level"] == 30 and cfg["version"] == SCHEMA_VERSION
    cfg["duck"] = False
    cfg.save()
    assert Config()["duck"] is False  # afterwards the user's choice is respected


def test_ancient_flat_config_migrates_and_keeps_the_output_device():
    write({"device": "CABLE Input (VB-Audio Virtual Cable)", "slots": {"97": {"name": "x", "file": ""}}})
    cfg = Config()
    assert cfg["device"].startswith("CABLE Input") and cfg.slot(97)["name"] == "x" and cfg["duck"] is True
