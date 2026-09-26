# Third-party notices

HERMETIKS Soundboard itself is MIT licensed. It is built with and redistributes the following
open source components. Each remains under its own license; full texts are available from the
projects listed and inside the corresponding Python packages.

| Component | Use | License |
|---|---|---|
| Python | runtime | PSF-2.0 |
| Tcl/Tk (tkinter) | user interface | Tcl/Tk License (BSD-style) |
| NumPy | audio maths | BSD-3-Clause |
| sounddevice, PortAudio | audio output | MIT |
| SoundFile, libsndfile | decoding wav/mp3/ogg/flac | BSD-3-Clause, LGPL-2.1 |
| PyAV, FFmpeg libraries | decoding m4a/webm/aac | BSD-3-Clause, LGPL-3.0-or-later |
| Pillow | images | MIT-CMU (HPND) |
| pystray | tray icon | LGPL-3.0 |
| pycaw, comtypes | ducking (Windows audio sessions) | MIT |
| pywinrt (winrt-*) | Now Playing (Windows media controls) | MIT |
| yt-dlp | import from video/audio pages | The Unlicense |
| BBH Bartle | wordmark typeface | SIL Open Font License 1.1 |
| Rethink Sans | interface typeface | SIL Open Font License 1.1 |

Build tools (not redistributed inside the app): PyInstaller (GPL-2.0-or-later with the bootloader
exception, which permits distributing non-GPL programs), Inno Setup (Inno Setup License), fontTools (MIT).

## LGPL components
libsndfile, the FFmpeg libraries and pystray are licensed under the LGPL. In the installed
application they are kept as separate files (DLLs / Python modules inside the `_internal` folder),
so you may replace them with your own builds. Their source code is available from their upstream
projects (https://ffmpeg.org, https://libsndfile.github.io/libsndfile/, https://pypi.org/project/pystray/).

## Fonts
The typefaces are distributed under the SIL Open Font License 1.1. The license texts are in
`hermetiks/resources/fonts/OFL-BBHBartle.txt` and `OFL-RethinkSans.txt`.
