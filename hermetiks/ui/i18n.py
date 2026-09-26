"""Translations. Locale files live in ui/locales/<code>.json; English is the source and the fallback."""
import json
import os

from ..paths import locale_dir

LANGUAGES = {"en": "English", "es": "Español", "zh": "中文", "pt": "Português"}
DEFAULT = "en"

_tables = {}
_current = DEFAULT


def _table(code):
    if code not in _tables:
        try:
            with open(os.path.join(locale_dir(), f"{code}.json"), encoding="utf-8") as f:
                _tables[code] = json.load(f)
        except (OSError, ValueError):
            _tables[code] = {}
    return _tables[code]


def set_language(code):
    global _current
    _current = code if code in LANGUAGES else DEFAULT


def language():
    return _current


def t(key, **params):
    text = _table(_current).get(key) or _table(DEFAULT).get(key) or key
    return text.format(**params) if params else text
