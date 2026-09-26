/* HERMETIKS Now Playing overlay renderer. Shared by the app's local server and the website widget.
   HermetiksOverlay.start({ source, interval, demoCover, authMessage })
   `source()` resolves to { id, title, artist, img, dur, prog, playing, at } or null (nothing playing).
   It may reject with an Error carrying `.code === "auth"` or a numeric `.retryAfter` (ms).
   URL options: ?layout=stack  ?scale=1.5  ?bg=0  ?demo=1 */
(function (root) {
  "use strict";
  var q = new URLSearchParams(location.search);
  var $ = function (id) { return document.getElementById(id); };

  /* Served by the app itself: same origin. Opened as a file (OBS "Local file") or elsewhere: use the app on 127.0.0.1. */
  var servedByApp = location.protocol === "http:" && /^(127\.0\.0\.1|localhost)$/.test(location.hostname);
  var BASE = servedByApp ? "" : "http://127.0.0.1:" + (parseInt(q.get("port"), 10) || 8765) + "/";

  function localSource() {
    return fetch(BASE + "api/now-playing", { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    }).then(function (j) {
      if (!j || !j.active) return null;
      return { id: j.id, title: j.title, artist: j.artist, img: j.cover ? BASE + j.cover + "&t=" + encodeURIComponent(j.id) : "",
               dur: j.duration_ms || 0, prog: j.position_ms || 0, playing: !!j.playing, at: Date.now() };
    });
  }

  function start(opts) {
    opts = opts || {};
    document.body.classList.add("overlay");
    if (q.get("layout") === "stack") document.body.classList.add("stack");
    if (q.get("bg") === "0") document.body.classList.add("no-panel");
    var scale = parseFloat(q.get("scale"));
    if (scale > 0.2 && scale < 6) document.documentElement.style.setProperty("--scale", scale);
    $("stage").hidden = false;

    var np = $("np"), cover = $("cover"), current = null, snap = null;
    function message(text) { var e = $("err"); if (e) { e.textContent = text || ""; e.hidden = !text; } }
    function fit(el) {
      var s = el.firstElementChild; el.classList.remove("scroll"); s.style.removeProperty("--d");
      var over = s.scrollWidth - el.clientWidth;
      if (over > 4) { el.classList.add("scroll"); s.style.setProperty("--d", over + 24 + "px"); s.style.paddingRight = "24px"; }
      else { s.style.paddingRight = "0"; }
    }
    function setTrack(t) {
      snap = t;
      if (!t) { np.classList.add("hide"); current = null; return; }
      if (current !== t.id) {
        current = t.id;
        np.classList.add("swap");
        setTimeout(function () {
          $("title").firstElementChild.textContent = t.title;
          $("artist").firstElementChild.textContent = t.artist;
          cover.src = t.img || ""; cover.style.visibility = t.img ? "visible" : "hidden";
          np.classList.remove("swap", "hide");
          requestAnimationFrame(function () { fit($("title")); fit($("artist")); });
        }, 320);
      } else { np.classList.remove("hide"); if (t.img && cover.getAttribute("src") !== t.img && !cover.src) cover.src = t.img; }
    }
    setInterval(function () { /* smooth progress between polls */
      if (!snap || !snap.dur) return;
      var p = snap.prog + (snap.playing ? Date.now() - snap.at : 0);
      $("bar").style.width = Math.max(0, Math.min(100, p / snap.dur * 100)) + "%";
    }, 250);

    if (q.get("demo") === "1") {
      setTrack({ id: "demo", title: "Midnight Static", artist: "HERMETIKS Radio", img: opts.demoCover || "demo-cover.png",
                 dur: 214000, prog: 62000, playing: true, at: Date.now() });
      return;
    }
    var interval = opts.interval || 2000, failures = 0;
    (function poll() {
      var delay = interval;
      Promise.resolve().then(opts.source).then(function (t) { failures = 0; message(""); setTrack(t); if (!t) delay = interval * 2; })
        .catch(function (e) {
          if (e && e.code === "auth") { message(opts.authMessage || "Reconnect"); delay = 30000; }
          else {
            delay = (e && e.retryAfter) || Math.min(interval * 4, 10000);
            if (++failures >= 2 && opts.unreachableMessage) message(opts.unreachableMessage);  // never leave OBS blank without saying why
          }
        }).then(function () { setTimeout(poll, delay); });
    })();
  }

  root.HermetiksOverlay = { start: start, localSource: localSource };
  if (document.body && document.body.getAttribute("data-source") === "local") {
    var where = servedByApp ? location.origin + "/" : BASE;
    start({ source: localSource, interval: 1000,
            unreachableMessage: "HERMETIKS is not reachable. Open the app (Now Playing overlay ticked). In OBS use the URL " + where + " as the Browser source URL." });
  }
})(window);
