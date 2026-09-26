# Privacy

HERMETIKS Soundboard is designed to work entirely on your computer.

- **No data collection.** No accounts, no analytics, no telemetry, no advertising.
- **Keyboard input.** To react to your shortcuts while a game has focus, the app reads keyboard events through Windows Raw Input
  (and, only if you enable "Block keys for the game", a low-level keyboard hook). Each key press is only compared with your configured shortcuts and
  discarded. Keystrokes are never stored, logged or transmitted.
- **Network access.** The app only connects to the internet when *you* import audio from a link
  (a direct audio URL, or a page supported by yt-dlp such as YouTube). Nothing else is sent anywhere.
- **Other apps' volume.** If you enable Duck, the app temporarily lowers the volume of the
  applications you list (default: `spotify.exe`) through the Windows audio session API, and restores it afterwards.
- **Now Playing overlay (optional).** If you enable it, the app reads the current track from the Windows media
  controls (for example Spotify desktop) and serves it to a local web page for OBS at `http://127.0.0.1:<port>`.
  The server listens on the loopback address only and rejects requests for other host names; nothing is sent over the network.
- **Local files.** Settings and imported sounds are stored in `%APPDATA%\Hermetiks`. The uninstaller
  offers to remove them.

Contact: https://hermetiks.orilladiseno.cl
