(function () {
  "use strict";
  var REPO = "orilladiseno-jpg/hermetiks";
  var T = window.HERMETIKS_I18N || {};
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- language ---------- */
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  function pick() {
    var saved = store("lang");
    if (saved && T[saved]) return saved;
    var n = (navigator.language || "en").toLowerCase();
    return n.indexOf("es") === 0 ? "es" : n.indexOf("pt") === 0 ? "pt" : n.indexOf("zh") === 0 ? "zh" : "en";
  }
  function setLang(code) {
    var d = T[code] || T.en;
    document.documentElement.lang = code;
    $$("[data-i18n]").forEach(function (el) {
      var v = d[el.getAttribute("data-i18n")] || T.en[el.getAttribute("data-i18n")];
      if (v) el.textContent = v;
    });
    if (!document.body.classList.contains("doc")) {
      document.title = d["meta.title"];
      var m = $('meta[name="description"]');
      if (m) m.setAttribute("content", d["meta.desc"]);
    }
    var sel = $("#lang");
    if (sel) sel.value = code;
    if (window.__ver) $("#ver").textContent = window.__ver;
    store("lang", code);
  }
  var sel = $("#lang");
  if (sel) sel.addEventListener("change", function () { setLang(sel.value); });
  setLang(pick());

  /* ---------- nav shadow + reveal ---------- */
  var nav = $(".nav");
  var onScroll = function () { nav.classList.toggle("scrolled", window.scrollY > 8); };
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    $$(".card, .steps li, details, .pad-wrap, .hero-shot").forEach(function (el) { el.classList.add("rv"); io.observe(el); });
  }

  /* ---------- optional hero video: shown only if the file exists ---------- */
  var vid = $(".shot-video"), img = $(".shot-img");
  if (vid) {
    vid.addEventListener("loadeddata", function () { vid.hidden = false; if (img) img.hidden = true; });
    vid.load();
  }

  /* ---------- latest release from GitHub (falls back to the releases page) ---------- */
  fetch("https://api.github.com/repos/" + REPO + "/releases/latest", { headers: { Accept: "application/vnd.github+json" } })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (rel) {
      if (!rel) return;
      var asset = (rel.assets || []).filter(function (a) { return /Setup.*\.exe$/i.test(a.name); })[0];
      if (asset) $$(".js-download").forEach(function (a) { a.href = asset.browser_download_url; });
      var mb = asset ? " · " + (asset.size / 1048576).toFixed(0) + " MB" : "";
      window.__ver = rel.tag_name + mb;
      var v = $("#ver"); if (v) v.textContent = window.__ver;
    })
    .catch(function () {});

  /* ---------- live demo: synthesized sounds, nothing is downloaded ---------- */
  var pad = $("#pad");
  if (!pad) return;
  var FILES = { "1": "jingle", "2": "station", "3": "weather", "4": "headlines", "5": "applause",
                "6": "drop", "7": "sting", "8": "outro", "9": "static", "0": "onair" };
  var ctx, master, analyser, active = [], raw = {}, bufs = {};
  function audio() {
    if (!ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      master = ctx.createGain(); master.gain.value = 0.9;
      analyser = ctx.createAnalyser(); analyser.fftSize = 1024;
      master.connect(analyser); analyser.connect(ctx.destination);
      draw();
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  /* the MP3 files are fetched once the demo comes near the viewport, decoded on the first key press */
  function fetchAll() {
    Object.keys(FILES).forEach(function (k) {
      if (raw[k]) return;
      raw[k] = fetch("assets/audio/" + FILES[k] + ".mp3").then(function (r) { return r.ok ? r.arrayBuffer() : null; }).catch(function () { return null; });
    });
  }
  function buffer(k) {
    if (bufs[k]) return bufs[k];
    fetchAll();
    bufs[k] = raw[k].then(function (ab) { return ab ? new Promise(function (ok, no) { ctx.decodeAudioData(ab, ok, no); }) : null; }).catch(function () { return null; });
    return bufs[k];
  }
  function stopAll() {
    active.forEach(function (n) { try { n.stop(); } catch (e) {} });
    active = [];
  }
  function flash(k) {
    var b = $('.key[data-key="' + k + '"]', pad); if (!b) return;
    b.classList.add("on"); setTimeout(function () { b.classList.remove("on"); }, 160);
  }
  function play(k) {
    if (!audio()) return;
    if (k === ".") { stopAll(); flash(k); return; }
    if (!FILES[k]) return;
    flash(k);
    Object.keys(FILES).forEach(buffer); /* warm every clip on first use */
    buffer(k).then(function (buf) {
      if (!buf) return;
      var s = ctx.createBufferSource(); s.buffer = buf; s.connect(master); s.start();
      active.push(s);
      s.onended = function () { active = active.filter(function (n) { return n !== s; }); };
    });
  }
  if ("IntersectionObserver" in window) {
    var near = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { fetchAll(); near.disconnect(); } }, { rootMargin: "600px" });
    near.observe(pad);
  }
  pad.addEventListener("click", function (e) { var b = e.target.closest(".key"); if (b) play(b.getAttribute("data-key")); });
  document.addEventListener("keydown", function (e) {
    if (e.repeat || e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target && e.target.tagName; if (t === "INPUT" || t === "SELECT" || t === "TEXTAREA") return;
    var m = /^Numpad([0-9])$/.exec(e.code);
    if (m) { e.preventDefault(); play(m[1]); }
    else if (e.code === "NumpadDecimal" || e.code === "Escape") play(".");
  });

  /* oscilloscope */
  var cv = $("#scope"), c2 = cv && cv.getContext("2d");
  function draw() {
    if (!c2 || !analyser) return;
    requestAnimationFrame(draw);
    var w = cv.width, h = cv.height, data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    c2.clearRect(0, 0, w, h);
    c2.lineWidth = 2; c2.strokeStyle = "rgba(255,255,255,.9)"; c2.beginPath();
    for (var i = 0; i < data.length; i += 2) {
      var x = i / data.length * w, y = h / 2 + (data[i] - 128) / 128 * (h / 2 - 4);
      i === 0 ? c2.moveTo(x, y) : c2.lineTo(x, y);
    }
    c2.stroke();
  }
})();
