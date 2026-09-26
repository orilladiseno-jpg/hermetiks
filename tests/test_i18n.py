import json
import os
import re
import string

import pytest

from hermetiks.paths import locale_dir
from hermetiks.ui import i18n

CODES = list(i18n.LANGUAGES)


def load(code):
    with open(os.path.join(locale_dir(), f"{code}.json"), encoding="utf-8") as f:
        return json.load(f)


def fields(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


@pytest.mark.parametrize("code", CODES)
def test_same_keys_as_english(code):
    en, other = load("en"), load(code)
    assert set(other) == set(en), (set(en) ^ set(other))


@pytest.mark.parametrize("code", CODES)
def test_placeholders_match_english(code):
    en, other = load("en"), load(code)
    for key, text in en.items():
        assert fields(other[key]) == fields(text), f"{code}:{key}"


@pytest.mark.parametrize("code", CODES)
def test_no_empty_strings(code):
    assert all(v.strip() for v in load(code).values())


def test_every_key_used_in_code_exists():
    root = os.path.dirname(locale_dir())
    used = set()
    for name in ("main_window.py", "about.py", "tray.py"):
        with open(os.path.join(root, name), encoding="utf-8") as f:
            src = f.read()
        used |= set(re.findall(r'\bt\(\s*"([a-z_.]+)"', src))
        used |= set(re.findall(r'^\s*\("([a-z_]+\.[a-z_]+)",', src, flags=re.M))
    used |= {f"mode.{m}" for m in ("normal", "hold", "loop")}
    used |= {f"fx.{k}" for k in ("vol", "speed", "trim_in", "trim_out", "bass", "treble", "echo", "reverb",
                                 "radio", "robot", "reverse", "normalize")}
    missing = {k for k in used if k not in load("en")}
    assert not missing, missing


def test_fallback_to_english_then_key():
    i18n.set_language("zh")
    assert i18n.t("profile.label") == load("zh")["profile.label"]
    assert i18n.t("does.not.exist") == "does.not.exist"
    i18n.set_language("xx")
    assert i18n.language() == "en"
