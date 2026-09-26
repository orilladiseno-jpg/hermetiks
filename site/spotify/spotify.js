/* Spotify Now Playing for OBS. Pure static page: OAuth with PKCE (no client secret, no server).
   Modes:  /spotify/                     setup (connect once, get your OBS URL)
           /spotify/?cid=..&rt=..        overlay (what OBS renders)
           /spotify/?demo=1              overlay with fake data (to tune layout)
   Overlay options: &layout=stack  &scale=1.5  &bg=0
   Nothing is sent to HERMETIKS: the page talks only to accounts.spotify.com and api.spotify.com. */
(function (root) {
  "use strict";
  var AUTH = "https://accounts.spotify.com/authorize";
  var TOKEN = "https://accounts.spotify.com/api/token";
  var API = "https://api.spotify.com/v1/me/player/currently-playing?additional_types=episode";
  var SCOPE = "user-read-currently-playing";
  var K_PKCE = "hermetiks_spotify_pkce", K_RT = "hermetiks_spotify_rt_";

  /* ---------- PKCE helpers (pure, unit-tested) ---------- */
  function b64url(bytes) {
    var s = ""; for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
  function randomString(n) {
    var a = new Uint8Array(n); crypto.getRandomValues(a);
    return b64url(a).slice(0, n);
  }
  function pkceChallenge(verifier) {
    return crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)).then(function (d) { return b64url(new Uint8Array(d)); });
  }
  function pickImage(images) {
    if (!images || !images.length) return "";
    var s = images.slice().sort(function (a, b) { return (a.width || 0) - (b.width || 0); });
    var big = s.filter(function (i) { return (i.width || 0) >= 300; })[0];
    return (big || s[s.length - 1]).url;
  }
  function normalize(j) {
    if (!j || !j.item) return null;
    var it = j.item, ep = it.type === "episode";
    return {
      id: it.id || it.name, title: it.name,
      artist: ep ? (it.show && it.show.name) || "" : (it.artists || []).map(function (a) { return a.name; }).join(", "),
      img: pickImage(ep ? it.images : it.album && it.album.images),
      dur: it.duration_ms || 0, prog: j.progress_ms || 0, playing: !!j.is_playing, at: Date.now()
    };
  }
  if (typeof module !== "undefined" && module.exports) { module.exports = { b64url: b64url, pkceChallenge: pkceChallenge, pickImage: pickImage, normalize: normalize }; }
  if (typeof document === "undefined") return;

  /* ---------- page ---------- */
  var $ = function (id) { return document.getElementById(id); };
  var q = new URLSearchParams(location.search);
  var REDIRECT = location.origin + location.pathname;
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) {} }
  };
  var form = function (o) { return new URLSearchParams(o).toString(); };

  var TXT = {
    en: { eyebrow: "Free extra", title: "Spotify Now Playing for OBS",
      intro: "Shows the current song, artist and cover art in OBS with a subtle HERMETIKS mark. Free. It runs inside your OBS browser source and nothing is sent to us.",
      s1: "Create an app in the Spotify Developer Dashboard (choose Web API):", uri: "Set this Redirect URI exactly:", copy: "Copy", copied: "Copied",
      s2: "Paste the app's Client ID:", s3: "Connect your Spotify account (read-only: current track):", connect: "Connect Spotify",
      premium: "Spotify may require the app owner to have Premium, and your account to be listed under User Management in the app's settings.",
      doneTitle: "Connected. Your OBS URL is ready.", doneText: "In OBS add a Browser source, paste this URL, and set width 640 and height 240.",
      preview: "Preview", warn: "Treat this URL like a password: it lets anyone see what you are playing. Do not share it or show it on stream.",
      options: "Options: add &layout=stack for a vertical card, &scale=1.5 to resize, &bg=0 for no dark panel.",
      back: "Back to HERMETIKS", privacy: "Privacy", needCid: "Paste your Client ID first.", authErr: "Spotify could not connect: ",
      reconnect: "Spotify disconnected. Open the setup page to reconnect." },
    es: { eyebrow: "Extra gratis", title: "Spotify Now Playing para OBS",
      intro: "Muestra en OBS la canción, el artista y la portada con una marca HERMETIKS sutil. Gratis. Funciona dentro de tu fuente de navegador de OBS y no nos envía nada.",
      s1: "Crea una app en el Spotify Developer Dashboard (elige Web API):", uri: "Usa exactamente esta Redirect URI:", copy: "Copiar", copied: "Copiado",
      s2: "Pega el Client ID de la app:", s3: "Conecta tu cuenta de Spotify (solo lectura: canción actual):", connect: "Conectar Spotify",
      premium: "Spotify puede exigir que el dueño de la app tenga Premium y que tu cuenta esté en User Management, en los ajustes de la app.",
      doneTitle: "Conectado. Tu URL de OBS está lista.", doneText: "En OBS agrega una fuente Navegador, pega esta URL y usa ancho 640 y alto 240.",
      preview: "Vista previa", warn: "Trata esta URL como una contraseña: permite a cualquiera ver lo que escuchas. No la compartas ni la muestres en stream.",
      options: "Opciones: agrega &layout=stack para tarjeta vertical, &scale=1.5 para cambiar el tamaño, &bg=0 para quitar el panel oscuro.",
      back: "Volver a HERMETIKS", privacy: "Privacidad", needCid: "Primero pega tu Client ID.", authErr: "Spotify no pudo conectar: ",
      reconnect: "Spotify se desconectó. Abre la página de configuración para reconectar." },
    pt: { eyebrow: "Extra gratuito", title: "Spotify Now Playing para OBS",
      intro: "Mostra no OBS a música, o artista e a capa com uma marca HERMETIKS discreta. Gratuito. Funciona dentro da sua fonte de navegador do OBS e não nos envia nada.",
      s1: "Crie um app no Spotify Developer Dashboard (escolha Web API):", uri: "Use exatamente esta Redirect URI:", copy: "Copiar", copied: "Copiado",
      s2: "Cole o Client ID do app:", s3: "Conecte a sua conta do Spotify (somente leitura: música atual):", connect: "Conectar Spotify",
      premium: "O Spotify pode exigir que o dono do app tenha Premium e que a sua conta esteja em User Management, nas configurações do app.",
      doneTitle: "Conectado. A sua URL do OBS está pronta.", doneText: "No OBS adicione uma fonte Navegador, cole esta URL e use largura 640 e altura 240.",
      preview: "Pré-visualizar", warn: "Trate esta URL como uma senha: ela permite que qualquer pessoa veja o que você está ouvindo. Não a compartilhe nem a mostre na live.",
      options: "Opções: adicione &layout=stack para cartão vertical, &scale=1.5 para redimensionar, &bg=0 para remover o painel escuro.",
      back: "Voltar ao HERMETIKS", privacy: "Privacidade", needCid: "Cole primeiro o seu Client ID.", authErr: "O Spotify não conseguiu conectar: ",
      reconnect: "O Spotify foi desconectado. Abra a página de configuração para reconectar." },
    zh: { eyebrow: "免费附赠", title: "OBS 用 Spotify 正在播放",
      intro: "在 OBS 中显示当前歌曲、歌手和封面，并带有低调的 HERMETIKS 标志。免费。它运行在你的 OBS 浏览器源内，不会向我们发送任何数据。",
      s1: "在 Spotify Developer Dashboard 创建应用（选择 Web API）：", uri: "请原样设置此 Redirect URI：", copy: "复制", copied: "已复制",
      s2: "粘贴应用的 Client ID：", s3: "连接你的 Spotify 账号（只读：当前曲目）：", connect: "连接 Spotify",
      premium: "Spotify 可能要求应用所有者拥有 Premium，并要求你的账号已添加到应用设置的 User Management 中。",
      doneTitle: "已连接。你的 OBS 链接已生成。", doneText: "在 OBS 中添加“浏览器”来源，粘贴此链接，宽度设为 640、高度设为 240。",
      preview: "预览", warn: "请把此链接当作密码：任何人拿到它都能看到你在听什么。不要分享，也不要在直播中显示。",
      options: "选项：加 &layout=stack 为竖版卡片，&scale=1.5 调整大小，&bg=0 去掉深色底板。",
      back: "返回 HERMETIKS", privacy: "隐私", needCid: "请先粘贴 Client ID。", authErr: "Spotify 连接失败：",
      reconnect: "Spotify 已断开。请打开设置页面重新连接。" }
  };
  var lang = store.get("lang");
  if (!TXT[lang]) { var n = (navigator.language || "en").toLowerCase().slice(0, 2); lang = TXT[n] ? n : "en"; }
  var T = TXT[lang];
  var setErr = function (id, msg) { var e = $(id); e.textContent = msg; e.hidden = !msg; };

  /* ---------- setup ---------- */
  function showSetup() {
    document.body.classList.add("setup-mode");
    document.documentElement.lang = lang;
    Array.prototype.forEach.call(document.querySelectorAll("[data-s]"), function (el) { var v = T[el.getAttribute("data-s")]; if (v) el.textContent = v; });
    $("setup").hidden = false;
    $("redirect").textContent = REDIRECT;
    $("cid").value = store.get("hermetiks_spotify_cid") || "";
    var copy = function (text, btn) {
      var done = function () { var old = btn.textContent; btn.textContent = T.copied; setTimeout(function () { btn.textContent = old; }, 1400); };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, done); else done();
    };
    $("copyRedirect").onclick = function () { copy(REDIRECT, this); };
    $("copyUrl").onclick = function () { copy($("obsUrl").value, this); };
    $("connect").onclick = function () {
      var cid = $("cid").value.trim();
      if (!/^[0-9a-f]{32}$/i.test(cid)) { setErr("setupErr", T.needCid); return; }
      store.set("hermetiks_spotify_cid", cid);
      var verifier = randomString(96), state = randomString(16);
      store.set(K_PKCE, JSON.stringify({ verifier: verifier, state: state, cid: cid }));
      pkceChallenge(verifier).then(function (challenge) {
        location.href = AUTH + "?" + form({ response_type: "code", client_id: cid, scope: SCOPE, redirect_uri: REDIRECT,
          state: state, code_challenge_method: "S256", code_challenge: challenge });
      });
    };
  }
  function finishAuth(code, state) {
    var saved; try { saved = JSON.parse(store.get(K_PKCE)); } catch (e) { saved = null; }
    history.replaceState(null, "", location.pathname);
    if (!saved || saved.state !== state) { setErr("setupErr", T.authErr + "state"); return; }
    fetch(TOKEN, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form({ grant_type: "authorization_code", code: code, redirect_uri: REDIRECT, client_id: saved.cid, code_verifier: saved.verifier }) })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error_description || j.error || r.status); return j; }); })
      .then(function (j) {
        store.del(K_PKCE);
        var url = REDIRECT + "?" + form({ cid: saved.cid, rt: j.refresh_token });
        $("stepsBox").hidden = true; $("doneBox").hidden = false;
        $("obsUrl").value = url; $("preview").href = url;
      })
      .catch(function (e) { setErr("setupErr", T.authErr + e.message); });
  }

  /* ---------- overlay: the shared renderer (overlay.js) plus a Spotify Web API source ---------- */
  function spotifySource(cid, urlRt) {
    var access = null, expires = 0;
    function refresh() {
      var candidates = [store.get(K_RT + cid), urlRt].filter(function (v, i, a) { return v && a.indexOf(v) === i; });
      var attempt = function (i) {
        if (i >= candidates.length) { var e = new Error("invalid_grant"); e.code = "auth"; return Promise.reject(e); }
        return fetch(TOKEN, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: form({ grant_type: "refresh_token", refresh_token: candidates[i], client_id: cid }) })
          .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || r.status); return j; }); })
          .then(function (j) {
            access = j.access_token; expires = Date.now() + j.expires_in * 1000;
            store.set(K_RT + cid, j.refresh_token || candidates[i]);
          })
          .catch(function (e) { if (e.code === "auth") throw e; if (e.message === "invalid_grant" || e.message === "400") return attempt(i + 1); throw e; });
      };
      return attempt(0);
    }
    function fetchTrack() {
      return fetch(API, { headers: { Authorization: "Bearer " + access } }).then(function (r) {
        if (r.status === 204) return null;
        if (r.status === 200) return r.json().then(normalize);
        var e = new Error("http " + r.status);
        if (r.status === 401) access = null;
        if (r.status === 429) e.retryAfter = ((+r.headers.get("Retry-After")) || 5) * 1000 + 500;
        throw e;
      });
    }
    return function () { return (access && Date.now() < expires - 30000 ? Promise.resolve() : refresh()).then(fetchTrack); };
  }
  function startOverlay() {
    HermetiksOverlay.start({ source: spotifySource(q.get("cid"), q.get("rt")), interval: 3000, authMessage: T.reconnect });
  }

  /* ---------- router ---------- */
  if (q.get("demo") === "1" || (q.get("cid") && q.get("rt"))) startOverlay();
  else if (q.get("code") && q.get("state")) { showSetup(); finishAuth(q.get("code"), q.get("state")); }
  else if (q.get("error")) { showSetup(); setErr("setupErr", T.authErr + q.get("error")); history.replaceState(null, "", location.pathname); }
  else showSetup();
})(typeof window !== "undefined" ? window : globalThis);
