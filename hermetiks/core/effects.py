"""Offline effects chain. render() turns a decoded clip + settings into the buffer that gets mixed."""
import numpy as np

from .audio import SR, resample

DEFAULT_FX = dict(vol=100, speed=100, trim_in=0, trim_out=100, bass=0, treble=0,
                  echo=0, reverb=0, radio=False, robot=False, reverse=False, normalize=False)


def fx_radio(x):
    """Old-radio band-pass (350 Hz - 3.4 kHz) with soft saturation."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    mask = ((f > 350) & (f < 3400)).astype(np.float32)[:, None]
    y = np.fft.irfft(np.fft.rfft(x, axis=0) * mask, n, axis=0)
    return (np.tanh(y * 3.0) * 0.8).astype(np.float32)


def fx_robot(x):
    """Ring modulation at 55 Hz."""
    t = np.arange(len(x)) / SR
    m = np.sin(2 * np.pi * 55 * t)[:, None].astype(np.float32)
    return (x * m * 1.1 + x * 0.25).astype(np.float32)


def fx_eq(x, bass_db, treble_db):
    """Two-band shelving EQ in the frequency domain (corner ~250 Hz and ~3.5 kHz)."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    low = 1 / (1 + (f / 250.0) ** 4)
    high = 1 - 1 / (1 + (f / 3500.0) ** 4)
    gain = 1 + (10 ** (bass_db / 20) - 1) * low + (10 ** (treble_db / 20) - 1) * high
    return np.fft.irfft(np.fft.rfft(x, axis=0) * gain[:, None].astype(np.float32), n, axis=0).astype(np.float32)


def fx_echo(x, amount):
    delay, taps = int(0.28 * SR), 5
    out = np.zeros((len(x) + delay * taps, 2), np.float32)
    out[: len(x)] += x
    feedback = 0.5 + 0.3 * amount
    for i in range(1, taps + 1):
        out[i * delay: i * delay + len(x)] += x * ((feedback ** i) * (0.4 + 0.6 * amount))
    return out


def fx_reverb(x, amount):
    """Convolution reverb with a synthetic exponentially-decaying noise impulse response."""
    length = int(SR * (0.6 + 1.6 * amount))
    t = np.arange(length) / SR
    rng = np.random.default_rng(7)
    ir = rng.standard_normal((length, 2)) * np.exp(-t * (6 / (0.5 + 1.5 * amount)))[:, None]
    ir /= np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True))
    n = len(x) + length
    nfft = 1 << (n - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, nfft, axis=0) * np.fft.rfft(ir, nfft, axis=0), nfft, axis=0)[:n]
    dry = np.zeros((n, 2), np.float32)
    dry[: len(x)] = x
    return (dry * (1 - 0.5 * amount) + wet * (0.9 * amount)).astype(np.float32)


def render(base, fx):
    n = len(base)
    a, b = int(n * fx["trim_in"] / 100), int(n * fx["trim_out"] / 100)
    x = base[a:b] if b - a > 256 else base
    speed = fx["speed"] / 100
    if abs(speed - 1) > 0.01:
        x = resample(x, np.linspace(0, len(x) - 1, max(int(len(x) / speed), 2)))
    if fx["reverse"]:
        x = x[::-1]
    if fx["bass"] or fx["treble"]:
        x = fx_eq(x, fx["bass"], fx["treble"])
    if fx["robot"]:
        x = fx_robot(x)
    if fx["radio"]:
        x = fx_radio(x)
    if fx["echo"] > 0:
        x = fx_echo(x, fx["echo"] / 100)
    if fx["reverb"] > 0:
        x = fx_reverb(x, fx["reverb"] / 100)
    if fx["normalize"]:
        peak = float(np.abs(x).max())
        if peak > 0:
            x = x * (0.92 / peak)
    return np.ascontiguousarray(x * (fx["vol"] / 100), dtype=np.float32)
