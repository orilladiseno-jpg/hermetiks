# Landing page (hermetiks.orilladiseno.cl)

Static site: plain HTML, CSS and JavaScript. No build step, no frameworks, no trackers.

## Deploy on cPanel
1. cPanel > Domains > Create a domain: `hermetiks.orilladiseno.cl`. Note its document root (for example `public_html/hermetiks`).
2. cPanel > SSL/TLS Status > run AutoSSL for the new subdomain.
3. Upload the **contents** of this folder (or `dist/hermetiks-site.zip`, then Extract) into that document root, so `index.html` sits directly inside it.
4. Open https://hermetiks.orilladiseno.cl and check: the page loads over HTTPS, the language selector works, the numpad demo plays.

`.htaccess` forces HTTPS and adds security headers and caching (Apache). If a header breaks something, remove that line rather than the whole file.

## Download button
`assets/js/main.js` asks GitHub for the latest release of `orilladiseno-jpg/hermetiks` and points every download button to the installer
(`Hermetiks-Setup-*.exe`). Until the first release exists, buttons link to the Releases page.

## Optional hero video
Drop a short silent loop at `assets/video/hero.mp4` (H.264, about 1280x1080, under 4 MB). The hero shows it automatically
in place of the screenshot; without the file the screenshot is used. Replace `assets/img/app.png` when the app UI changes.

## Languages
Texts live in `assets/js/i18n.js` (English, Spanish, Chinese, Portuguese). Add a key to all four languages when adding text.
