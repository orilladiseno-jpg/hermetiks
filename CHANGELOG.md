# Changelog

## 1.1.0
- **Works in the background, always.** Hotkeys now use Windows Raw Input, so they keep working while HERMETIKS is minimized,
  in the tray or behind a game, and Windows can no longer drop them for being slow. The keyboard hook is installed only while
  "Block keys for the game" is on. HERMETIKS opts out of Windows 11 efficiency mode and runs a single instance.
- **Smooth ducking.** Music fades down in about 0.16 s and back up in about 0.5 s along a smooth curve instead of cutting.
  It finds Spotify on any output device (including VB-CABLE), is on by default, and restores your volume if the app closes mid-duck.
- **Mini overlay** for the streamer: a small click-through panel in the top-right corner listing your sounds and lighting up
  the one that plays. Not captured by OBS Game Capture.
- **Now Playing overlay for OBS**: song, artist and cover art from Spotify desktop (or any player with Windows media controls) with
  a subtle HERMETIKS mark. No login. "Save HTML for OBS" in the app writes a single file to use as an OBS local file.
  A web version using the Spotify Web API lives at /spotify/ on the website.
- Local diagnostic log (`%APPDATA%\Hermetiks\hermetiks.log`, never contains keystrokes or audio).
- Landing: downloads section, VirusTotal badge, demo with original MP3 clips.

## 1.0.0
- First public release.
- Global numpad hotkeys by scancode (work with NumLock on or off); any key can be assigned.
- Selectable WASAPI output plus optional monitor output; mixes with Spotify / Chrome.
- Per-slot volume, speed/pitch, trim with waveform, bass/treble, echo, reverb, old radio, robot, reverse, normalize.
- Modes: normal, hold, loop. Duck: lowers other apps while a clip plays.
- Profiles, import from files, direct links and YouTube.
- Interface in English, Spanish, Chinese and Portuguese.
- Windows installer (English, Spanish, Portuguese) and portable build.
