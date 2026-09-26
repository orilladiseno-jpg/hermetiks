# Architecture

```
run.py / python -m hermetiks
        |
hermetiks/ui            FRONTEND (tkinter)                hermetiks/core           BACKEND (no GUI)
  __init__.run()  ----> MainWindow  ---- calls ---------> Session  (controller)
  main_window.py        about.py, tray.py                  |- Config      settings, profiles, migrations
  theme.py  i18n.py     locales/*.json                     |- Hook        global keyboard hook (scancodes)
                                                           |- Out         WASAPI stream + voice mixer
        ^                                                  |- Ducker      lowers other apps' volume
        |                                                  |- audio / effects / importer
        +------------- Session.events (thread-safe queue) -+
```

## Backend (`hermetiks/core`)
- **Session** is the only object the UI talks to. It owns the outputs, the decoded clips, the key map, the
  hook and the ducker. It never imports tkinter; the UI is notified through `Session.events`
  (`flash`, `refresh`, `status`, `imported`, `captured`).
- **Hook** runs a `WH_KEYBOARD_LL` hook on its own thread and identifies keys by `(scancode, extended)`,
  which makes the numpad independent of NumLock and lets any key be assigned. The handler must return
  quickly; playback only appends a voice to the mixer.
- **Out / mixer**: one PortAudio stream per output (main and optional monitor). The audio callback mixes
  all active voices; clips are pre-rendered, so effects cost nothing at play time.
- **effects.render()** applies the chain: trim, speed, reverse, EQ, robot, radio, echo, reverb, normalize, volume.
  Changes are re-rendered on a worker thread; a generation counter drops stale results.
- **Config** persists `%APPDATA%\Hermetiks\config.json` atomically and migrates older schemas.

## Frontend (`hermetiks/ui`)
- `MainWindow` is presentation only. Language changes rebuild the widget tree from `i18n.t()`.
- Translations are `locales/<code>.json`, English being the source and fallback.
  `tests/test_i18n.py` guarantees identical keys and placeholders across languages.
- `theme.py` holds the palette (black / white / greys) and loads BBH Bartle and Rethink Sans privately for
  the process (no font installation).

## Brand and packaging
- `tools/make_logo.py` generates the whole brand kit (SVG, PNG, ICO, wizard images) from one geometry
  definition plus the two font files.
- `tools/build.py` produces the PyInstaller app folder, the Inno Setup installer (`installer/hermetiks.iss`),
  the portable zip and `SHA256SUMS.txt`. The same script runs in CI.

## Threads
UI thread (tkinter) | hook thread | PortAudio callback | ducker thread | short-lived loader / render / download threads.
Shared state is limited to: the mixer voice list (locked), the clip caches (atomic dict writes) and `Session.events`.
