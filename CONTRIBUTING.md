# Contributing

HERMETIKS is open source (MIT). Issues and pull requests are welcome.

## Set up
    py -m pip install -e .[dev]
    py -m pytest

## Layout
    hermetiks/core/   backend: audio, effects, mixer, hotkeys, config, Session (no GUI imports)
    hermetiks/ui/     frontend: tkinter window, theme, translations (ui/locales/*.json)
    tests/            pytest suite (fake audio output; no sound card or keyboard needed)
    tools/            make_logo.py (brand kit from one geometry), build.py (exe + installer)
    installer/        Inno Setup script, wizard images, localized info pages
    brand/            logo, wordmark and icon source files

See `docs/ARCHITECTURE.md` for how the pieces fit together.

## Rules of thumb
- Keep `hermetiks/core` free of tkinter imports so it stays testable.
- Any new UI text goes in **all four** locale files; `tests/test_i18n.py` enforces matching keys and placeholders.
- The look is strictly black, white and greys. No accent colors, no emojis.
- Don't edit files in `brand/` or the logo files in `resources/` by hand: change `tools/make_logo.py` and re-run it.
