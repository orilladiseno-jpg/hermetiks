"""Audio file decoding and waveform helpers. Everything is float32 stereo at SR."""
import numpy as np
import soundfile as sf

SR = 48000


def _stereo(data):
    if data.shape[1] == 1:
        return np.repeat(data, 2, axis=1)
    return data[:, :2]


def resample(x, positions):
    """Linear-interpolate stereo audio `x` at fractional sample `positions`."""
    idx = np.arange(len(x))
    return np.stack([np.interp(positions, idx, x[:, c]) for c in range(2)], axis=1).astype(np.float32)


def _decode_av(path):
    import av  # bundles FFmpeg: m4a / webm / aac and anything libsndfile can't read
    container = av.open(path)
    resampler = av.AudioResampler(format="flt", layout="stereo", rate=SR)
    chunks = []
    for frame in container.decode(audio=0):
        for out in resampler.resample(frame):
            chunks.append(out.to_ndarray().reshape(-1, 2))
    for out in resampler.resample(None):
        chunks.append(out.to_ndarray().reshape(-1, 2))
    container.close()
    return np.concatenate(chunks).astype(np.float32)


def load_audio(path):
    try:
        data, sr = sf.read(path, dtype="float32", always_2d=True)
    except Exception:  # noqa: BLE001
        return _decode_av(path)
    data = _stereo(data)
    if sr != SR:
        data = resample(data, np.linspace(0, len(data) - 1, max(int(len(data) * SR / sr), 2)))
    return data


def envelope(x, bins=560):
    """Peak envelope for drawing a waveform."""
    mono = np.abs(x).max(axis=1)
    per_bin = len(mono) // bins
    if per_bin == 0:
        return np.zeros(bins, np.float32)
    return mono[: per_bin * bins].reshape(bins, per_bin).max(axis=1)
