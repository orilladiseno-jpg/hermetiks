"""Build the Windows release: app folder, installer, portable zip and SHA256SUMS.

    py tools/build.py            full release build
    py tools/build.py --brand    regenerate the brand kit first (tools/make_logo.py)
    py tools/build.py --no-installer

Requires: pip install -e .[dev]   and Inno Setup 6 (for the installer).
"""
import argparse
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from hermetiks import COLLECTIVE, COMPANY, COPYRIGHT, __version__  # noqa: E402

DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")
APP_DIR = os.path.join(DIST, "Hermetiks")


def version_file():
    v = tuple(int(p) for p in __version__.split(".")) + (0,) * (4 - len(__version__.split(".")))
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={v}, prodvers={v}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{COMPANY} - {COLLECTIVE}'),
      StringStruct('FileDescription', 'HERMETIKS Soundboard'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', 'Hermetiks'),
      StringStruct('LegalCopyright', '{COPYRIGHT}. MIT License.'),
      StringStruct('OriginalFilename', 'Hermetiks.exe'),
      StringStruct('ProductName', 'HERMETIKS Soundboard'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ])
"""
    os.makedirs(BUILD, exist_ok=True)
    path = os.path.join(BUILD, "version_info.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def pyinstaller():
    res = os.path.join("hermetiks", "resources")
    shutil.copy2(os.path.join(ROOT, "LICENSE"), os.path.join(ROOT, res, "LICENSE.txt"))
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", "Hermetiks",
            "--icon", os.path.join(ROOT, res, "icon.ico"), "--version-file", version_file(),
            "--distpath", DIST, "--workpath", BUILD, "--specpath", BUILD,
            "--add-data", f"{os.path.join(ROOT, res)};hermetiks/resources",
            "--add-data", f"{os.path.join(ROOT, 'hermetiks', 'ui', 'locales')};hermetiks/ui/locales",
            "--add-data", f"{os.path.join(ROOT, 'THIRD_PARTY_NOTICES.md')};.",
            "--add-data", f"{os.path.join(ROOT, 'PRIVACY.md')};.",
            "--collect-all", "sounddevice", "--collect-all", "soundfile", "--collect-all", "av",
            "--collect-all", "yt_dlp", "--collect-all", "pycaw", "--hidden-import", "pystray._win32",
            "--exclude-module", "matplotlib", "--exclude-module", "scipy", "--exclude-module", "pandas",
            "--exclude-module", "pytest", os.path.join(ROOT, "run.py")]
    subprocess.check_call(args, cwd=ROOT)


def iscc():
    candidates = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe")) + \
        glob.glob(r"C:\Program Files*\Inno Setup 6\ISCC.exe") + [shutil.which("iscc") or ""]
    exe = next((c for c in candidates if c and os.path.exists(c)), None)
    if not exe:
        sys.exit("Inno Setup 6 not found. Install it: winget install JRSoftware.InnoSetup")
    subprocess.check_call([exe, f"/DAppVersion={__version__}", os.path.join(ROOT, "installer", "hermetiks.iss")])


def portable_zip():
    path = os.path.join(DIST, f"Hermetiks-portable-{__version__}.zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for folder, _, files in os.walk(APP_DIR):
            for name in files:
                full = os.path.join(folder, name)
                z.write(full, os.path.join("Hermetiks", os.path.relpath(full, APP_DIR)))
        for doc in ("LICENSE", "THIRD_PARTY_NOTICES.md", "PRIVACY.md", "TRADEMARKS.md"):
            z.write(os.path.join(ROOT, doc), os.path.join("Hermetiks", doc))
    return path


def checksums(paths):
    lines = []
    for p in paths:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        lines.append(f"{h.hexdigest()}  {os.path.basename(p)}")
    with open(os.path.join(DIST, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", action="store_true", help="regenerate the brand kit first")
    ap.add_argument("--no-installer", action="store_true")
    opts = ap.parse_args()
    if opts.brand:
        subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "make_logo.py")])
    shutil.rmtree(DIST, ignore_errors=True)
    pyinstaller()
    outputs = [portable_zip()]
    if not opts.no_installer:
        iscc()
        versioned = os.path.join(DIST, f"Hermetiks-Setup-{__version__}.exe")
        stable = os.path.join(DIST, "Hermetiks-Setup.exe")  # stable name for releases/latest/download/
        shutil.copy2(versioned, stable)
        outputs[:0] = [versioned, stable]
    checksums(outputs)


if __name__ == "__main__":
    main()
