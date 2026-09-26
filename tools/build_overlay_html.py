"""Build one self-contained HTML file for OBS: site/downloads/hermetiks-nowplaying.html

CSS, JavaScript, fonts and logo are inlined, so the file works from OBS > Browser source > "Local file".
It reads the current track from the HERMETIKS app (Now Playing overlay enabled) at http://127.0.0.1:8765
(change with ?port=NNNN). Layout options: ?layout=stack  ?scale=1.5  ?bg=0  ?demo=1
"""
import base64
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "hermetiks", "resources", "overlay")
FONTS = os.path.join(ROOT, "hermetiks", "resources", "fonts")
OUT = os.path.join(ROOT, "site", "downloads", "hermetiks-nowplaying.html")


def read(*parts, mode="r"):
    with open(os.path.join(*parts), mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def data_uri(mime, data):
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def main():
    css = read(SRC, "overlay.css")
    for name in ("RethinkSans-Medium.ttf", "RethinkSans-Bold.ttf"):
        css = css.replace(f'url("fonts/{name}")', f'url("{data_uri("font/ttf", read(FONTS, name, mode="rb"))}")')
    js = read(SRC, "overlay.js")
    js = js.replace('"demo-cover.png"', '"' + data_uri("image/png", read(SRC, "demo-cover.png", mode="rb")) + '"')
    body = read(SRC, "index.html")
    body = body[body.index("<body"):body.index("<script")]
    body = body.replace('src="lockup-white.svg"', f'src="{data_uri("image/svg+xml", read(SRC, "lockup-white.svg", mode="rb"))}"')
    html = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<title>HERMETIKS Now Playing</title>\n"
            "<!-- HERMETIKS Now Playing for OBS. Requires the HERMETIKS app (1.1 or newer) running with 'Now Playing overlay' ticked. -->\n"
            f"<style>\n{css}</style>\n</head>\n{body}<script>\n{js}</script>\n</body>\n</html>\n")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"wrote {OUT} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
