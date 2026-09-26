"""Now Playing: reads the current track from Windows' media session and serves an OBS overlay on localhost.

Works with Spotify for desktop (no login, no developer app), and any player that reports to the Windows
media controls. Everything stays on this computer: the server binds to 127.0.0.1 only.
"""
import asyncio
import hashlib
import json
import os
import socket
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..paths import resource

PLAYING = 4  # GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING


def track_id(title, artist, album):
    return hashlib.sha1(f"{title}|{artist}|{album}".encode("utf-8")).hexdigest()[:12]


class MediaProvider(threading.Thread):
    """Polls the Windows media sessions about once a second. Thread-safe `snapshot()`."""

    def __init__(self, prefer="spotify"):
        super().__init__(daemon=True, name="hermetiks-nowplaying")
        self.prefer = prefer.lower()
        self.running = True
        self.error = None
        self._lock = threading.Lock()
        self._info = None
        self._cover = b""
        self._cover_key = None

    def snapshot(self):
        with self._lock:
            return (dict(self._info) if self._info else None), self._cover

    def stop(self):
        self.running = False

    def run(self):
        try:
            asyncio.run(self._loop())
        except Exception as ex:  # noqa: BLE001
            self.error = str(ex)

    async def _loop(self):
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
        manager = await Manager.request_async()
        while self.running:
            try:
                await self._tick(manager)
            except Exception:  # noqa: BLE001 - a session can disappear between calls
                pass
            await asyncio.sleep(1.0)

    def _publish(self, info, cover=None):
        with self._lock:
            self._info = info
            if cover is not None:
                self._cover = cover

    async def _tick(self, manager):
        sessions = list(manager.get_sessions())
        chosen = next((s for s in sessions if self.prefer in (s.source_app_user_model_id or "").lower()), None)
        chosen = chosen or manager.get_current_session()
        if chosen is None:
            self._publish(None)
            return
        props = await chosen.try_get_media_properties_async()
        title, artist, album = props.title or "", props.artist or "", props.album_title or ""
        if not title:
            self._publish(None)
            return
        playing = int(chosen.get_playback_info().playback_status) == PLAYING
        timeline = chosen.get_timeline_properties()
        position = timeline.position.total_seconds() * 1000
        duration = timeline.end_time.total_seconds() * 1000
        if playing:  # SMTC reports the position at `last_updated_time`; advance it to "now"
            try:
                position += (datetime.now(timezone.utc) - timeline.last_updated_time).total_seconds() * 1000
            except Exception:  # noqa: BLE001
                pass
        key = track_id(title, artist, album)
        cover = None
        if key != self._cover_key:
            cover = await self._read_cover(props)
            self._cover_key = key
        self._publish({"active": True, "id": key, "title": title, "artist": artist, "album": album,
                       "playing": playing, "position_ms": int(max(0, min(position, duration or position))),
                       "duration_ms": int(duration), "app": chosen.source_app_user_model_id}, cover)

    @staticmethod
    async def _read_cover(props):
        if not props.thumbnail:
            return b""
        try:
            from winrt.windows.storage.streams import DataReader
            stream = await props.thumbnail.open_read_async()
            reader = DataReader(stream)
            await reader.load_async(stream.size)
            data = bytearray(stream.size)
            reader.read_bytes(data)
            return bytes(data)
        except Exception:  # noqa: BLE001
            return b""


OVERLAY_FILES = {"/": "index.html", "/index.html": "index.html", "/overlay.css": "overlay.css", "/overlay.js": "overlay.js",
                 "/lockup-white.svg": "lockup-white.svg", "/demo-cover.png": "demo-cover.png"}
FONTS = {"RethinkSans-Medium.ttf", "RethinkSans-Bold.ttf"}
# "null": file:// page; "http://absolute": how OBS (CEF) serves a Browser source set to "Local file"
ALLOWED_ORIGINS = {"null", "http://absolute", "https://hermetiks.orilladiseno.cl"}
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
        ".svg": "image/svg+xml", ".png": "image/png", ".ttf": "font/ttf"}


def sniff_image(data):
    if data[:4] == b"\x89PNG":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF":
        return "image/webp"
    return "application/octet-stream"


def make_handler(provider, port_holder):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Hermetiks"
        sys_version = ""

        def log_message(self, *args):  # silence
            pass

        def _send(self, status, body, ctype, cache="no-store"):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            origin = self.headers.get("Origin")
            if origin in ALLOWED_ORIGINS:  # the standalone OBS file runs from file:// (origin "null")
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def _file(self, path, cache="no-store"):
            try:
                with open(path, "rb") as f:
                    body = f.read()
            except OSError:
                return self._send(404, b"Not found", "text/plain")
            self._send(200, body, MIME.get(os.path.splitext(path)[1], "application/octet-stream"), cache)

        def do_OPTIONS(self):  # CORS / Private Network Access preflight
            origin = self.headers.get("Origin")
            self.send_response(204)
            if origin in ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.send_header("Access-Control-Allow-Private-Network", "true")
                self.send_header("Vary", "Origin")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            port = port_holder["port"]
            if self.headers.get("Host", "") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                return self._send(421, b"Misdirected request", "text/plain")  # blocks DNS-rebinding
            path = self.path.split("?", 1)[0]
            if path in OVERLAY_FILES:
                return self._file(resource("overlay", OVERLAY_FILES[path]))
            if path.startswith("/fonts/") and path[7:] in FONTS:
                return self._file(resource("fonts", path[7:]), "public, max-age=86400")
            if path == "/api/now-playing":
                info, cover = provider.snapshot()
                body = {"active": False} if not info else {**info, "cover": "api/cover?v=1" if cover else ""}
                return self._send(200, json.dumps(body).encode("utf-8"), "application/json")
            if path == "/api/cover":
                _, cover = provider.snapshot()
                if not cover:
                    return self._send(404, b"", "text/plain")
                return self._send(200, cover, sniff_image(cover))
            self._send(404, b"Not found", "text/plain")

    return Handler


class _Server(ThreadingHTTPServer):
    """Exclusive loopback port: on Windows SO_REUSEADDR would let another process bind the same port."""
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class NowPlaying:
    """Provider + local HTTP server. `start()` returns the OBS Browser Source URL."""

    def __init__(self, port=8765, provider=None):
        self.provider = provider or MediaProvider()
        self.preferred_port = port
        self.server = None
        self._thread = None

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_address[1]}/" if self.server else None

    def start(self):
        holder = {"port": 0}
        handler = make_handler(self.provider, holder)
        last = None
        for offset in range(0, 20) if self.preferred_port else (0,):  # busy port: try the next ones
            try:
                self.server = _Server(("127.0.0.1", self.preferred_port + offset), handler)
                break
            except OSError as ex:
                last = ex
        else:
            raise last
        holder["port"] = self.server.server_address[1]
        if isinstance(self.provider, threading.Thread) and not self.provider.is_alive():
            self.provider.start()
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="hermetiks-overlay-http")
        self._thread.start()
        return self.url

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if hasattr(self.provider, "stop"):
            self.provider.stop()
