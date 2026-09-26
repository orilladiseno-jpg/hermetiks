"""Copy the shared overlay (hermetiks/resources/overlay + 2 fonts) into site/spotify/.

The app's local server and the website widget render the same overlay; the source of truth is
hermetiks/resources/overlay. tests/test_nowplaying.py fails if the site copy is stale.
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "hermetiks", "resources", "overlay")
FONTS = os.path.join(ROOT, "hermetiks", "resources", "fonts")
DST = os.path.join(ROOT, "site", "spotify")
SHARED = ["overlay.css", "overlay.js", "lockup-white.svg", "demo-cover.png"]
SHARED_FONTS = ["RethinkSans-Medium.ttf", "RethinkSans-Bold.ttf"]


def main():
    os.makedirs(os.path.join(DST, "fonts"), exist_ok=True)
    for name in SHARED:
        shutil.copy2(os.path.join(SRC, name), os.path.join(DST, name))
    for name in SHARED_FONTS:
        shutil.copy2(os.path.join(FONTS, name), os.path.join(DST, "fonts", name))
    print("overlay synced to site/spotify")


if __name__ == "__main__":
    main()
