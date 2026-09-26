# Privacy

HERMETIKS Soundboard is designed to work entirely on your computer.

- **No data collection.** No accounts, no analytics, no telemetry, no advertising.
- **Keyboard hook.** To react to your shortcuts while a game has focus, the app installs a Windows
  low-level keyboard hook. Each key press is only compared with your configured shortcuts and
  discarded. Keystrokes are never stored, logged or transmitted.
- **Network access.** The app only connects to the internet when *you* import audio from a link
  (a direct audio URL, or a page supported by yt-dlp such as YouTube). Nothing else is sent anywhere.
- **Other apps' volume.** If you enable Duck, the app temporarily lowers the volume of the
  applications you list (default: `spotify.exe`) through the Windows audio session API, and restores it afterwards.
- **Local files.** Settings and imported sounds are stored in `%APPDATA%\Hermetiks`. The uninstaller
  offers to remove them.

Contact: https://hermetiks.orilladiseno.cl
