"""Backend behaviour with a fake audio output: no sound card or keyboard hook needed."""
import numpy as np
import pytest

from hermetiks.core.session import Session
from hermetiks.core.slots import DEFAULT_KEYS, DEFAULT_STOP, ESCAPE_KEY, NO_KEY


class FakeOut:
    def __init__(self):
        self.voices = []
        self.master = 1.0
        self.peak = 0.0

    def play(self, data, slot, loop=False):
        self.voices.append((slot, loop))

    def playing(self, slot):
        return any(s == slot for s, _ in self.voices)

    def stop_slot(self, slot):
        self.voices = [v for v in self.voices if v[0] != slot]

    def stop(self):
        self.voices = []

    @property
    def busy(self):
        return bool(self.voices)

    def close(self):
        pass


@pytest.fixture
def session():
    s = Session()
    s.outs = [FakeOut()]
    s.rebuild_keymap()
    for slot in (97, 98, 99):
        s.cache[slot] = np.zeros((100, 2), np.float32)
    return s


def press(s, key, down=True):
    return s.on_key(key, down)


def test_default_numpad_keys_trigger_their_slots(session):
    press(session, DEFAULT_KEYS[97])
    assert session.outs[0].playing(97)


def test_auto_repeat_is_ignored_until_release(session):
    press(session, DEFAULT_KEYS[97]); press(session, DEFAULT_KEYS[97]); press(session, DEFAULT_KEYS[97])
    assert len(session.outs[0].voices) == 1
    press(session, DEFAULT_KEYS[97], False); press(session, DEFAULT_KEYS[97])
    assert len(session.outs[0].voices) == 2


def test_stop_key_silences_everything(session):
    press(session, DEFAULT_KEYS[97]); press(session, DEFAULT_KEYS[98])
    press(session, DEFAULT_STOP)
    assert not session.outs[0].busy


def test_hold_mode_stops_on_release(session):
    session.cfg.slot(98)["mode"] = "hold"
    press(session, DEFAULT_KEYS[98])
    assert session.outs[0].playing(98)
    press(session, DEFAULT_KEYS[98], False)
    assert not session.outs[0].playing(98)


def test_loop_mode_toggles(session):
    session.cfg.slot(99)["mode"] = "loop"
    press(session, DEFAULT_KEYS[99]); press(session, DEFAULT_KEYS[99], False)
    assert session.outs[0].voices == [(99, True)]
    press(session, DEFAULT_KEYS[99])
    assert not session.outs[0].playing(99)


def test_slot_without_audio_does_nothing(session):
    press(session, DEFAULT_KEYS[100])
    assert not session.outs[0].busy


def test_inactive_shortcuts_pass_keys_through(session):
    session.cfg["active"] = False
    assert press(session, DEFAULT_KEYS[97]) is False
    assert not session.outs[0].busy


def test_suppress_swallows_only_mapped_keys(session):
    session.cfg["suppress"] = True
    assert press(session, DEFAULT_KEYS[97]) is True
    assert press(session, (0x1E, 0)) is False  # unrelated key: always passes through


def test_capture_assigns_any_key_and_swallows_it(session):
    session.start_capture(97)
    assert press(session, (0x1E, 0)) is True
    kind, target, key = session.events.get_nowait()
    assert (kind, target, key) == ("captured", 97, (0x1E, 0))
    session.apply_captured(97, key)
    assert session.slot_key(97) == (0x1E, 0)
    press(session, (0x1E, 0))
    assert session.outs[0].playing(97)
    assert DEFAULT_KEYS[97] not in session.keymap


def test_assigning_a_used_key_steals_it(session):
    session.apply_captured(97, DEFAULT_KEYS[98])
    assert session.slot_key(98) == NO_KEY and session.slot_key(97) == DEFAULT_KEYS[98]


def test_escape_cancels_assignment(session):
    session.apply_captured(97, ESCAPE_KEY)
    assert session.slot_key(97) == DEFAULT_KEYS[97]


def test_stop_key_can_be_reassigned(session):
    session.apply_captured("stop", (0x39, 0))
    assert session.stop_key() == (0x39, 0)
    press(session, DEFAULT_KEYS[97]); press(session, (0x39, 0))
    assert not session.outs[0].busy


def test_reset_key_restores_numpad_default(session):
    session.apply_captured(97, (0x1E, 0))
    session.reset_key(97)
    assert session.slot_key(97) == DEFAULT_KEYS[97]


def test_profiles_keep_separate_key_maps(session):
    session.apply_captured(97, (0x1E, 0))
    session.cfg.add_profile("Other")
    session.switch_profile("Other")
    assert session.slot_key(97) == DEFAULT_KEYS[97]
    session.switch_profile("Main")
    assert session.slot_key(97) == (0x1E, 0)


def test_hook_only_swallows_configured_keys_and_never_triggers(session):
    session.cfg["suppress"] = True
    assert session.swallow(DEFAULT_KEYS[97], True) is True
    assert session.swallow(DEFAULT_STOP, True) is True
    assert session.swallow((0x1E, 0), True) is False
    assert not session.outs[0].busy  # deciding to swallow must not play anything
    session.cfg["suppress"] = False
    assert session.swallow(DEFAULT_KEYS[97], True) is False


def test_raw_input_path_triggers_without_the_hook(session):
    session.handle_key(DEFAULT_KEYS[97], True)
    assert session.outs[0].playing(97)
    session.handle_key(DEFAULT_STOP, True)
    assert not session.outs[0].busy


def test_set_suppress_is_a_noop_without_raw_input(session):
    session.set_suppress(True)
    assert session.hook is None


def test_dead_output_is_reopened_on_the_next_key_press(session, monkeypatch):
    class Dead(FakeOut):
        class stream:  # noqa: N801
            active = False
    session.outs = [Dead()]
    reopened = []

    def fake_rebuild():
        session.outs = [FakeOut()]
        reopened.append(1)
        return ["Speakers"], []
    monkeypatch.setattr(session, "rebuild_outputs", fake_rebuild)
    session.trigger(97, True)
    assert reopened == [1] and session.outs[0].playing(97)
    session.outs[0].stream = type("S", (), {"active": False})()
    session.trigger(97, True)
    assert reopened == [1]  # throttled: not more than once every 2 seconds
