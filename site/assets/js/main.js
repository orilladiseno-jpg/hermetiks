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
  var ctx, master, analyser, active = [];
  function audio() {
    if (!ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      master = ctx.createGain(); master.gain.value = 0.55;
      analyser = ctx.createAnalyser(); analyser.fftSize = 1024;
      master.connect(analyser); analyser.connect(ctx.destination);
      draw();
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  function env(g, t, a, d, peak) {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + a);
    g.gain.exponentialRampToValueAtTime(0.0001, t + a + d);
  }
  function tone(type, f0, f1, t, dur, peak) {
    var o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type; o.frequency.setValueAtTime(f0, t);
    if (f1) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    env(g, t, 0.01, dur, peak);
    o.connect(g); g.connect(master); o.start(t); o.stop(t + dur + 0.05); active.push(o);
  }
  var noiseBuf;
  function noise(t, dur, peak, lo, hi) {
    if (!noiseBuf) {
      noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
      var d = noiseBuf.getChannelData(0); for (var i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    var s = ctx.createBufferSource(); s.buffer = noiseBuf;
    var f = ctx.createBiquadFilter(); f.type = "bandpass"; f.frequency.value = (lo + hi) / 2; f.Q.value = (lo + hi) / 2 / Math.max(hi - lo, 1);
    var g = ctx.createGain(); env(g, t, 0.02, dur, peak);
    s.connect(f); f.connect(g); g.connect(master); s.start(t); s.stop(t + dur + 0.1); active.push(s);
  }
  var N = { C5: 523.25, E5: 659.25, G5: 783.99, C6: 1046.5, A4: 440, D5: 587.33, F5: 698.46, B4: 493.88 };
  var voices = {
    "1": function (t) { [N.C5, N.E5, N.G5, N.C6].forEach(function (f, i) { tone("triangle", f, 0, t + i * 0.11, 0.5, 0.35); }); },
    "2": function (t) { noise(t, 0.35, 0.25, 900, 2600); tone("sine", 1000, 0, t + 0.05, 0.16, 0.3); tone("sine", 1400, 0, t + 0.28, 0.2, 0.3); },
    "3": function (t) { [N.C5, N.E5, N.G5].forEach(function (f) { tone("sine", f / 2, 0, t, 1.6, 0.22); }); },
    "4": function (t) { tone("sawtooth", 220, 660, t, 0.45, 0.16); tone("sawtooth", 330, 990, t, 0.45, 0.12); noise(t + 0.4, 0.4, 0.12, 2000, 6000); },
    "5": function (t) { for (var i = 0; i < 26; i++) noise(t + Math.random() * 1.6, 0.06 + Math.random() * 0.08, 0.18, 1500, 5500); },
    "6": function (t) { tone("sine", 180, 38, t, 0.7, 0.7); noise(t, 0.12, 0.25, 100, 400); },
    "7": function (t) { tone("sawtooth", N.C5, 0, t, 0.5, 0.2); tone("sawtooth", N.G5, 0, t, 0.5, 0.16); tone("sawtooth", N.C6, 0, t, 0.5, 0.12); },
    "8": function (t) { [N.G5, N.E5, N.D5, N.C5].forEach(function (f, i) { tone("triangle", f, 0, t + i * 0.13, 0.55, 0.3); }); },
    "9": function (t) { noise(t, 1.2, 0.3, 300, 7000); },
    "0": function (t) { tone("sawtooth", 233, 0, t, 0.9, 0.22); tone("sawtooth", 277, 0, t, 0.9, 0.18); tone("square", 349, 0, t, 0.9, 0.08); }
  };
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
    if (voices[k]) { voices[k](ctx.currentTime + 0.01); flash(k); }
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
