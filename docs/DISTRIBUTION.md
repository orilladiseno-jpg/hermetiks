# Distributing HERMETIKS safely

## What we publish
| File | For |
|---|---|
| `Hermetiks-Setup-x.y.z.exe` | Recommended. Per-user install (no admin), Start menu / desktop shortcut, uninstaller. Wizard in English, Spanish and Portuguese. |
| `Hermetiks-portable-x.y.z.zip` | No install: unzip and run `Hermetiks.exe`. |
| `SHA256SUMS.txt` | Hashes of both files. |

## Integrity
1. Releases are built by the GitHub Actions workflow from the public source (`.github/workflows/release.yml`), not on a personal computer.
2. The website links to the GitHub Release; it never hosts a separate binary.
3. Users can verify a download with `Get-FileHash <file> -Algorithm SHA256` against `SHA256SUMS.txt`.

## Antivirus and SmartScreen
The app uses a global keyboard hook to react to hotkeys in games, which heuristic scanners treat with
suspicion when the binary is unsigned. What we do about it:
- Ship an app *folder* (not a self-extracting one-file exe), which triggers far fewer false positives.
- Fill in the executable's version information (company, product, copyright) and keep the source public.
- Scan every release on VirusTotal and link the report in the release notes.
- **Sign the binaries.** Options: SignPath Foundation (free for open source projects), Azure Trusted
  Signing (paid, per month) or an OV/EV code-signing certificate. Signing the installer *and* `Hermetiks.exe`
  removes the SmartScreen warning once reputation builds. Add the signing step to `tools/build.py` / the workflow
  after the PyInstaller and Inno Setup steps.
- If a vendor flags a release, submit it as a false positive to that vendor with the source link.

## Release checklist
1. Update `hermetiks/__init__.py` version and `CHANGELOG.md`.
2. `py -m pytest` is green.
3. Tag `vX.Y.Z` and push: CI builds and publishes.
4. Upload the installer to VirusTotal, add the link to the release notes.
5. Update the download link and hashes on the website.
