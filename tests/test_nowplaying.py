import filecmp
import json
import os
import urllib.error
import urllib.request

import pytest

from hermetiks.core.nowplaying import NowPlaying, sniff_image, track_id
from hermetiks.paths import PACKAGE_DIR

ROOT = os.path.dirname(PACKAGE_DIR)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


class FakeProvider:
    def __init__(self, info=None, cover=b""):
        self.info, self.cover = info, cover

    def snapshot(self):
        return self.info, self.cover


TRACK = {"active": True, "id": track_id("Song", "Artist", "Album"), "title": "Song", "artist": "Artist", "album": "Album",
         "playing": True, "position_ms": 1000, "duration_ms": 200000, "app": "Spotify.exe"}


@pytest.fixture
def service():
    made = []

    def make(provider):
        s = NowPlaying(port=0, provider=provider)
        s.start()
        made.append(s)
        return s
    yield make
    for s in made:
        s.stop()


def get(service, path, host=None):
    req = urllib.request.Request(service.url.rstrip("/") + path)
    if host:
        req.add_header("Host", host)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def test_binds_to_loopback_only(service):
    s = service(FakeProvider())
    assert s.url.startswith("http://127.0.0.1:")
    assert s.server.server_address[0] == "127.0.0.1"


def test_api_reports_the_current_track(service):
    s = service(FakeProvider(TRACK, PNG))
    status, headers, body = get(s, "/api/now-playing")
    data = json.loads(body)
    assert status == 200 and headers["Content-Type"] == "application/json" and headers["Cache-Control"] == "no-store"
    assert data["title"] == "Song" and data["artist"] == "Artist" and data["playing"] is True
    assert data["cover"].startswith("api/cover")


def test_api_when_nothing_plays(service):
    s = service(FakeProvider(None))
    assert json.loads(get(s, "/api/now-playing")[2]) == {"active": False}
    assert get(s, "/api/cover")[0] == 404


def test_cover_is_served_with_the_right_type(service):
    s = service(FakeProvider(TRACK, PNG))
    status, headers, body = get(s, "/api/cover")
    assert status == 200 and headers["Content-Type"] == "image/png" and body == PNG


def test_no_cover_field_when_track_has_no_art(service):
    s = service(FakeProvider(TRACK, b""))
    assert json.loads(get(s, "/api/now-playing")[2])["cover"] == ""


def test_overlay_page_and_assets_are_served(service):
    s = service(FakeProvider())
    for path, ctype in (("/", "text/html"), ("/overlay.css", "text/css"), ("/overlay.js", "application/javascript"),
                        ("/lockup-white.svg", "image/svg+xml"), ("/fonts/RethinkSans-Bold.ttf", "font/ttf")):
        status, headers, _ = get(s, path)
        assert status == 200 and headers["Content-Type"].startswith(ctype), path


def test_foreign_host_header_is_rejected(service):
    s = service(FakeProvider(TRACK, PNG))  # DNS-rebinding protection
    assert get(s, "/api/now-playing", host="evil.example")[0] == 421
    assert get(s, "/api/now-playing", host=f"localhost:{s.server.server_address[1]}")[0] == 200


@pytest.mark.parametrize("path", ["/fonts/OFL-RethinkSans.txt", "/fonts/../fonts/RethinkSans-Bold.ttf",
                                  "/../pyproject.toml", "/config.json", "/api/unknown"])
def test_only_whitelisted_paths_are_served(service, path):
    assert get(service(FakeProvider()), path)[0] == 404


def test_stop_releases_the_port(service):
    s = service(FakeProvider())
    url = s.url
    s.stop()
    with pytest.raises(Exception):
        urllib.request.urlopen(url, timeout=1)


def test_busy_preferred_port_falls_through_to_the_next(service):
    first = service(FakeProvider())
    port = first.server.server_address[1]
    second = NowPlaying(port=port, provider=FakeProvider())
    try:
        second.start()
        assert second.server.server_address[1] != port
    finally:
        second.stop()


def test_track_id_is_stable_and_distinct():
    assert track_id("a", "b", "c") == track_id("a", "b", "c") != track_id("a", "b", "d")


def test_sniff_image():
    assert sniff_image(PNG) == "image/png" and sniff_image(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert sniff_image(b"nope") == "application/octet-stream"


def test_website_overlay_copy_is_in_sync():
    """Run `py tools/sync_overlay.py` if this fails."""
    src = os.path.join(PACKAGE_DIR, "resources", "overlay")
    dst = os.path.join(ROOT, "site", "spotify")
    for name in ("overlay.css", "overlay.js", "lockup-white.svg", "demo-cover.png"):
        assert filecmp.cmp(os.path.join(src, name), os.path.join(dst, name), shallow=False), name
    for name in ("RethinkSans-Medium.ttf", "RethinkSans-Bold.ttf"):
        assert filecmp.cmp(os.path.join(PACKAGE_DIR, "resources", "fonts", name), os.path.join(dst, "fonts", name), shallow=False)


def test_standalone_obs_html_is_self_contained():
    """`py tools/build_overlay_html.py` output: works as an OBS local file, no external hosts."""
    import re
    path = os.path.join(ROOT, "site", "downloads", "hermetiks-nowplaying.html")
    html = open(path, encoding="utf-8").read()
    assert 'data-source="local"' in html and "api/now-playing" in html
    assert "url(fonts/" not in html and 'src="lockup-white.svg"' not in html and '"demo-cover.png"' not in html
    hosts = set(re.findall(r"https?://([a-z0-9.\-]+)", html))
    assert hosts <= {"127.0.0.1", "www.w3.org"}, hosts


def test_cors_only_for_file_origin_and_the_website(service):
    s = service(FakeProvider(TRACK, PNG))

    def origin(value):
        req = urllib.request.Request(s.url + "api/now-playing", headers={"Origin": value})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.headers.get("Access-Control-Allow-Origin")
    assert origin("null") == "null"  # OBS "Local file"
    assert origin("https://hermetiks.orilladiseno.cl") == "https://hermetiks.orilladiseno.cl"
    assert origin("https://evil.example") is None


def test_obs_local_file_origin_is_allowed_and_preflight_answers(service):
    s = service(FakeProvider(TRACK, PNG))
    req = urllib.request.Request(s.url + "api/now-playing", headers={"Origin": "http://absolute"})
    with urllib.request.urlopen(req, timeout=5) as r:  # OBS (CEF) serves "Local file" sources from this origin
        assert r.headers["Access-Control-Allow-Origin"] == "http://absolute"
    pre = urllib.request.Request(s.url + "api/now-playing", method="OPTIONS",
                                 headers={"Origin": "http://absolute", "Access-Control-Request-Method": "GET"})
    with urllib.request.urlopen(pre, timeout=5) as r:
        assert r.status == 204 and r.headers["Access-Control-Allow-Origin"] == "http://absolute"
        assert r.headers["Access-Control-Allow-Private-Network"] == "true"
