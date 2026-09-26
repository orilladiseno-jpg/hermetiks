# Security policy

## Reporting a vulnerability
Please do not open a public issue for security problems. Contact us through
https://hermetiks.orilladiseno.cl and include the version, Windows version and steps to reproduce.
We aim to acknowledge reports within 7 days.

## Downloading safely
- Only download HERMETIKS from the official website or the project's GitHub Releases page.
- Every release publishes a `SHA256SUMS.txt`. Verify your download in PowerShell:

      Get-FileHash .\Hermetiks-Setup-1.0.0.exe -Algorithm SHA256

  and compare it with the value in `SHA256SUMS.txt`.
- Release binaries are built from the public source by the CI workflow in `.github/workflows/`.
- Because the app uses a global keyboard hook (like any soundboard or macro tool), some antivirus
  products may flag unsigned builds heuristically. See `docs/DISTRIBUTION.md`.
