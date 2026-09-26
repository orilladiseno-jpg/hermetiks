"""Output devices and the real-time mixer (one PortAudio stream per output)."""
import threading

import numpy as np
import sounddevice as sd

from .audio import SR

MAX_VOICES = 24


def output_devices():
    """(name, index, is_wasapi) for output devices. WASAPI only: low latency, mixes with Spotify/Chrome."""
    wasapi = next((i for i, h in enumerate(sd.query_hostapis()) if "WASAPI" in h["name"]), None)
    devices = sd.query_devices()
    if wasapi is None:
        return [(d["name"], i, False) for i, d in enumerate(devices) if d["max_output_channels"] > 0]
    return [(d["name"], i, True) for i, d in enumerate(devices)
            if d["hostapi"] == wasapi and d["max_output_channels"] > 0]


def default_device_name():
    for h in sd.query_hostapis():
        if "WASAPI" in h["name"] and h["default_output_device"] >= 0:
            return sd.query_devices(h["default_output_device"])["name"]
    return None


class Voice:
    __slots__ = ("data", "pos", "slot", "loop")

    def __init__(self, data, slot, loop):
        self.data, self.pos, self.slot, self.loop = data, 0, slot, loop


class Out:
    """A single output stream mixing any number of voices. Thread-safe."""

    def __init__(self, index, wasapi):
        self.lock = threading.Lock()
        self.voices = []
        self.master = 1.0
        self.peak = 0.0
        extra = sd.WasapiSettings(auto_convert=True) if wasapi else None
        self.stream = sd.OutputStream(samplerate=SR, device=index, channels=2, dtype="float32",
                                      latency="low", callback=self._callback, extra_settings=extra)
        self.stream.start()

    def _callback(self, outdata, frames, _time, _status):
        outdata.fill(0)
        with self.lock:
            for v in self.voices[:]:
                offset, need = 0, frames
                while need > 0:
                    chunk = v.data[v.pos: v.pos + need]
                    k = len(chunk)
                    outdata[offset: offset + k] += chunk
                    v.pos += k
                    offset += k
                    need -= k
                    if v.pos >= len(v.data):
                        if v.loop and len(v.data) > 0:
                            v.pos = 0
                        else:
                            self.voices.remove(v)
                            break
        outdata *= self.master
        np.clip(outdata, -1, 1, out=outdata)
        self.peak = max(float(np.abs(outdata).max()), self.peak * 0.9)

    def play(self, data, slot, loop=False):
        with self.lock:
            self.voices.append(Voice(data, slot, loop))
            del self.voices[:-MAX_VOICES]

    def playing(self, slot):
        with self.lock:
            return any(v.slot == slot for v in self.voices)

    def stop_slot(self, slot):
        with self.lock:
            self.voices[:] = [v for v in self.voices if v.slot != slot]

    def stop(self):
        with self.lock:
            self.voices.clear()

    @property
    def busy(self):
        return bool(self.voices)

    def close(self):
        self.stream.stop()
        self.stream.close()
