"""Import audio from a direct link or, via yt-dlp, from a video/audio page."""
import os
import time
import urllib.request
from urllib.parse import urlparse

AUDIO_EXT = (".wav", ".mp3", ".ogg", ".flac", ".aiff", ".aif", ".opus", ".m4a", ".webm", ".aac")


class _Quiet:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def fetch_url(url, dest_dir):
    """Download `url` into `dest_dir`. Returns (path, title). Only http(s) is accepted."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http(s) links are supported")
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext in AUDIO_EXT:
        dest = os.path.join(dest_dir, f"dl{int(time.time())}{ext}")
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response, open(dest, "wb") as f:
            f.write(response.read())
        return dest, os.path.splitext(os.path.basename(parsed.path))[0]
    import yt_dlp
    options = {"format": "bestaudio/best", "outtmpl": os.path.join(dest_dir, "%(id)s.%(ext)s"),
               "noplaylist": True, "quiet": True, "no_warnings": True, "logger": _Quiet()}
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info), info.get("title", "audio")
