import numpy as np
import pytest

from hermetiks.core.audio import SR, envelope
from hermetiks.core.effects import DEFAULT_FX, render


@pytest.fixture
def tone():
    t = np.arange(SR) / SR
    mono = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return np.stack([mono, mono], axis=1)


def fx(**over):
    return {**DEFAULT_FX, **over}


def test_defaults_are_identity(tone):
    assert np.allclose(render(tone, fx()), tone)


def test_volume_scales(tone):
    assert np.isclose(np.abs(render(tone, fx(vol=50))).max(), np.abs(tone).max() / 2, atol=1e-4)


def test_speed_changes_length(tone):
    assert len(render(tone, fx(speed=200))) == pytest.approx(len(tone) / 2, abs=2)
    assert len(render(tone, fx(speed=50))) == pytest.approx(len(tone) * 2, abs=2)


def test_trim(tone):
    assert len(render(tone, fx(trim_in=25, trim_out=75))) == pytest.approx(len(tone) / 2, abs=2)


def test_reverse(tone):
    ramp = np.linspace(0, 1, 1000, dtype=np.float32)
    clip = np.stack([ramp, ramp], axis=1)
    assert np.allclose(render(clip, fx(reverse=True)), clip[::-1])


def test_echo_and_reverb_extend_the_tail(tone):
    assert len(render(tone, fx(echo=60))) > len(tone)
    assert len(render(tone, fx(reverb=60))) > len(tone)


def test_normalize_hits_target_peak(tone):
    assert np.isclose(np.abs(render(tone * 0.1, fx(normalize=True))).max(), 0.92, atol=1e-3)


@pytest.mark.parametrize("name", ["radio", "robot"])
def test_voice_filters_keep_shape_and_stay_finite(tone, name):
    out = render(tone, fx(**{name: True}))
    assert out.shape == tone.shape and np.isfinite(out).all()


def test_eq_boosts_low_frequencies():
    t = np.arange(SR) / SR
    low = np.stack([0.2 * np.sin(2 * np.pi * 80 * t)] * 2, axis=1).astype(np.float32)
    assert np.abs(render(low, fx(bass=12))).max() > np.abs(low).max() * 2


def test_envelope_length():
    assert len(envelope(np.ones((SR, 2), np.float32), 560)) == 560
