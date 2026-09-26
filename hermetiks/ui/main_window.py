"""Main window. Pure presentation: every action is delegated to the Session (backend)."""
import queue
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageTk

from ..core import importer, log, mixer, startup
import webbrowser
from ..core.effects import DEFAULT_FX
from ..core.hotkeys import key_name
from ..core.slots import MODES, SLOTS, SLOT_IDS
from ..paths import resource
from . import theme
from .about import About
from .hud import Hud
from .i18n import LANGUAGES, language, set_language, t
from .theme import BG, KEY, KEY_HI, MUTED, PANEL, TEXT, WHITE, button, caption, checkbox, font, slider
from .tray import Tray

LABELS = dict(SLOTS)
LAYOUT = {111: (0, 0), 106: (0, 1), 109: (0, 2),
          103: (1, 0), 104: (1, 1), 105: (1, 2), 107: (1, 3),
          100: (2, 0), 101: (2, 1), 102: (2, 2),
          97: (3, 0), 98: (3, 1), 99: (3, 2), 96: (4, 0)}
# (fx key, min, max, column)
SLIDERS = [("vol", 0, 200, 0), ("speed", 50, 200, 0), ("trim_in", 0, 95, 0), ("trim_out", 5, 100, 0),
           ("bass", -12, 12, 1), ("treble", -12, 12, 1), ("echo", 0, 100, 1), ("reverb", 0, 100, 1)]
CHECKS = ("radio", "robot", "reverse", "normalize")
WAVE_W, WAVE_H = 560, 84
LOGO_WIDTH = 270


class MainWindow:
    def __init__(self, root, session, start_hidden=False):
        self.root, self.s, self.cfg = root, session, session.cfg
        self.selected = SLOTS[0][0]
        self.tray = None
        self._loading = False
        self._job = None
        self._status = None
        self._alive = True
        self.hud = Hud(root, session)
        self._build()
        self.s.start()
        self.hud.set_enabled(self.cfg["hud"])
        self._sync_nowplaying_ui()
        self.reopen_outputs()
        self.select(self.selected)
        try:
            self.tray = Tray(lambda: self.s.events.put(("show",)), lambda: self.s.events.put(("toggle",)),
                             lambda: self.s.events.put(("quit",)), lambda: self.cfg["active"])
        except Exception:  # noqa: BLE001 - tray is optional
            self.tray = None
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(40, self.poll)
        if start_hidden:
            self.root.withdraw()

    # ---- construction ---------------------------------------------------------------------
    def _build(self):
        r = self.root
        for child in r.winfo_children():
            child.destroy()
        r.title("HERMETIKS Soundboard")
        r.configure(bg=BG)
        r.resizable(False, False)
        try:
            r.iconbitmap(default=resource("icon.ico"))
        except tk.TclError:
            pass
        theme.style_ttk(r)
        self.buttons, self.vars = {}, {}

        self._make_page()
        self._build_header()
        self._build_profile_bar()
        body = tk.Frame(self.page, bg=BG)
        body.pack(padx=28, pady=6)
        self._build_pad(body)
        self._build_editor(body)
        self._build_footer()
        self.refresh_all_buttons()
        self._fit_window()

    def _make_page(self):
        """A canvas that holds the whole UI, so short screens (laptops) can scroll instead of cutting the window."""
        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.page = tk.Frame(self.canvas, bg=BG)
        self._page_id = self.canvas.create_window((0, 0), window=self.page, anchor="nw")
        self.page.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.root.bind_all("<MouseWheel>", self._wheel)

    def _wheel(self, event):
        first, last = self.canvas.yview()
        if first > 0 or last < 1:
            self.canvas.yview_scroll(int(-event.delta / 120) * 2, "units")

    def _fit_window(self):
        self.root.update_idletasks()
        w, h = self.page.winfo_reqwidth(), self.page.winfo_reqheight()
        avail = self.root.winfo_screenheight() - 110  # title bar + taskbar
        self.canvas.configure(width=w, height=min(h, avail))
        self.root.resizable(False, h > avail)

    def _build_header(self):
        head = tk.Frame(self.page, bg=BG)
        head.pack(pady=(14, 4))
        img = Image.open(resource("lockup-white.png"))
        img = img.resize((LOGO_WIDTH, int(img.height * LOGO_WIDTH / img.width)), Image.LANCZOS)
        self._logo = ImageTk.PhotoImage(img)
        tk.Label(head, image=self._logo, bg=BG).pack()

        top = tk.Frame(self.page, bg=BG)
        top.place(relx=1.0, x=-28, y=20, anchor="ne")
        self.lang_var = tk.StringVar(value=LANGUAGES[language()])
        lang = ttk.Combobox(top, textvariable=self.lang_var, values=list(LANGUAGES.values()), state="readonly", width=10)
        lang.pack(side="left")
        lang.bind("<<ComboboxSelected>>", lambda e: self.change_language())
        button(top, t("about.button"), lambda: About(self.root)).pack(side="left", padx=(8, 0))

    def _build_profile_bar(self):
        bar = tk.Frame(self.page, bg=BG)
        bar.pack(fill="x", padx=28, pady=(4, 2))
        tk.Label(bar, text=t("profile.label"), bg=BG, fg=MUTED, font=font(9)).pack(side="left")
        self.profile_var = tk.StringVar(value=self.cfg.profile)
        self.profile_box = ttk.Combobox(bar, textvariable=self.profile_var, state="readonly", width=22,
                                        values=self.cfg.profile_names)
        self.profile_box.pack(side="left", padx=8)
        self.profile_box.bind("<<ComboboxSelected>>", lambda e: self.switch_profile(self.profile_var.get()))
        for label, cmd in (("profile.new", self.new_profile), ("profile.rename", self.rename_profile),
                           ("profile.delete", self.delete_profile)):
            button(bar, t(label), cmd).pack(side="left", padx=3)
        self.active = tk.BooleanVar(value=self.cfg["active"])
        checkbox(bar, t("shortcuts_active"), self.active, self.options_changed).pack(side="right")

    def _build_pad(self, body):
        pad = tk.Frame(body, bg=BG)
        pad.grid(row=0, column=0, sticky="n", padx=(0, 26))
        for slot, label in SLOTS:
            row, col = LAYOUT[slot]
            b = tk.Button(pad, text=label, width=9, height=3, relief="flat", bd=0, bg=KEY, fg=TEXT,
                          activebackground=KEY_HI, activeforeground=WHITE, font=font(9),
                          command=lambda s=slot: self.select(s))
            b.grid(row=row, column=col, columnspan=2 if slot == 96 else 1, rowspan=2 if slot == 107 else 1,
                   sticky="nsew", padx=3, pady=3)
            b.bind("<Double-Button-1>", lambda e, s=slot: self.s.trigger(s, True))
            self.buttons[slot] = b
        self.stop_btn = tk.Button(pad, relief="flat", bd=0, bg=WHITE, fg=BG, activebackground=TEXT,
                                  font=font(9, True), command=self.s.stop_all)
        self.stop_btn.grid(row=4, column=2, columnspan=2, sticky="nsew", padx=3, pady=3)
        tk.Label(pad, text=t("pad.hint"), bg=BG, fg=MUTED, font=font(8), justify="left").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        button(pad, t("pad.change_stop"), lambda: self.begin_capture("stop")).grid(
            row=5, column=2, columnspan=2, sticky="e", pady=(6, 0))

    def _build_editor(self, body):
        ed = tk.Frame(body, bg=PANEL, padx=20, pady=16)
        ed.grid(row=0, column=1, sticky="n")
        top = tk.Frame(ed, bg=PANEL)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.title_lbl = tk.Label(top, bg=PANEL, fg=WHITE, font=font(12, True))
        self.title_lbl.pack(side="left")
        button(top, t("editor.restore"), self.reset_key).pack(side="right", padx=(6, 0))
        button(top, t("editor.assign"), lambda: self.begin_capture(self.selected)).pack(side="right")

        row = tk.Frame(ed, bg=PANEL)
        row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        caption(row, t("editor.name"), PANEL).grid(row=0, column=0, sticky="w")
        caption(row, t("editor.mode"), PANEL).grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.name_var = tk.StringVar()
        tk.Entry(row, textvariable=self.name_var, bg=KEY, fg=WHITE, insertbackground=WHITE, relief="flat",
                 font=font(10), width=34).grid(row=1, column=0, sticky="ew", ipady=5)
        self.mode_var = tk.StringVar()
        mode = ttk.Combobox(row, textvariable=self.mode_var, values=[t(f"mode.{m}") for m in MODES],
                            state="readonly", width=12)
        mode.grid(row=1, column=1, padx=(12, 0))
        mode.bind("<<ComboboxSelected>>", lambda e: self.editor_changed(rerender=False))
        self.name_var.trace_add("write", lambda *_: self.editor_changed(rerender=False))

        self.file_lbl = tk.Label(ed, bg=PANEL, fg=MUTED, font=font(8), anchor="w")
        self.file_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        actions = tk.Frame(ed, bg=PANEL)
        actions.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 8))
        for label, cmd in (("editor.load", self.pick_file), ("editor.from_url", self.import_url),
                           ("editor.test", lambda: self.s.trigger(self.selected, True)),
                           ("editor.remove", self.clear_slot)):
            button(actions, t(label), cmd).pack(side="left", padx=(0, 6))

        self.wave = tk.Canvas(ed, width=WAVE_W, height=WAVE_H, bg=BG, highlightthickness=0)
        self.wave.grid(row=4, column=0, columnspan=2, pady=(0, 8))

        columns = [tk.Frame(ed, bg=PANEL), tk.Frame(ed, bg=PANEL)]
        columns[0].grid(row=5, column=0, sticky="n", padx=(0, 20))
        columns[1].grid(row=5, column=1, sticky="n")
        for key, lo, hi, col in SLIDERS:
            line = tk.Frame(columns[col], bg=PANEL)
            line.pack(anchor="w", pady=1)
            tk.Label(line, text=t(f"fx.{key}"), bg=PANEL, fg=MUTED, font=font(8), width=15, anchor="w").pack(side="left")
            var = tk.IntVar(value=DEFAULT_FX[key])
            self.vars[key] = var
            slider(line, var, lo, hi, 150, self.editor_changed).pack(side="left")
            tk.Label(line, textvariable=var, bg=PANEL, fg=WHITE, font=font(9), width=4, anchor="e").pack(side="left")
        checks = tk.Frame(ed, bg=PANEL)
        checks.grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))
        for key in CHECKS:
            var = tk.BooleanVar()
            self.vars[key] = var
            checkbox(checks, t(f"fx.{key}"), var, self.editor_changed, PANEL).pack(side="left", padx=(0, 16))

    def _build_footer(self):
        foot = tk.Frame(self.page, bg=BG)
        foot.pack(fill="x", padx=28, pady=(6, 14))
        names = [name for name, _, _ in mixer.output_devices()]
        default, none = t("output.default"), t("output.none")
        self.device_var = tk.StringVar(value=self.cfg["device"] or default)
        self.monitor_var = tk.StringVar(value=self.cfg["monitor"] or none)
        caption(foot, t("output.label")).grid(row=0, column=0, sticky="w")
        caption(foot, t("output.monitor")).grid(row=0, column=1, sticky="w", padx=(12, 0))
        caption(foot, t("output.master")).grid(row=0, column=2, sticky="w", padx=(12, 0))
        for col, (var, values) in enumerate(((self.device_var, [default] + names), (self.monitor_var, [none] + names))):
            box = ttk.Combobox(foot, textvariable=var, values=values, state="readonly", width=32)
            box.grid(row=1, column=col, padx=(12 if col else 0, 0), sticky="w")
            box.bind("<<ComboboxSelected>>", lambda e: self.options_changed(reopen=True))
        self.master_var = tk.IntVar(value=self.cfg["master"])
        slider(foot, self.master_var, 0, 100, 110, self.options_changed).grid(row=1, column=2, padx=(12, 0))
        self.meter = tk.Canvas(foot, width=110, height=6, bg=KEY, highlightthickness=0)
        self.meter.grid(row=2, column=2, padx=(12, 0), sticky="w")

        duck = tk.Frame(foot, bg=BG)
        duck.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 0))
        self.duck = tk.BooleanVar(value=self.cfg["duck"])
        checkbox(duck, t("duck.label"), self.duck, self.options_changed).pack(side="left")
        tk.Label(duck, text=t("duck.to"), bg=BG, fg=MUTED, font=font(9)).pack(side="left", padx=(10, 4))
        self.duck_level = tk.IntVar(value=self.cfg["duck_level"])
        slider(duck, self.duck_level, 0, 100, 90, self.options_changed).pack(side="left")
        tk.Label(duck, text=t("duck.percent_apps"), bg=BG, fg=MUTED, font=font(9)).pack(side="left", padx=(4, 6))
        self.duck_apps = tk.StringVar(value=self.cfg["duck_apps"])
        tk.Entry(duck, textvariable=self.duck_apps, bg=KEY, fg=WHITE, insertbackground=WHITE, relief="flat",
                 font=font(9), width=26).pack(side="left", ipady=3)
        self.duck_apps.trace_add("write", lambda *_: self.options_changed())

        opts = tk.Frame(foot, bg=BG)
        opts.grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.suppress = tk.BooleanVar(value=self.cfg["suppress"])
        self.close_tray = tk.BooleanVar(value=self.cfg["close_tray"])
        self.cfg["startup"] = startup.is_enabled()
        self.startup = tk.BooleanVar(value=self.cfg["startup"])
        self.hud_var = tk.BooleanVar(value=self.cfg["hud"])
        checkbox(opts, t("opt.suppress"), self.suppress, self.options_changed).pack(side="left", padx=(0, 16))
        checkbox(opts, t("opt.close_tray"), self.close_tray, self.options_changed).pack(side="left", padx=(0, 16))
        checkbox(opts, t("opt.startup"), self.startup, self.options_changed).pack(side="left", padx=(0, 16))
        checkbox(opts, t("opt.hud"), self.hud_var, self.options_changed).pack(side="left")
        self._build_nowplaying(foot)
        self.status_lbl = tk.Label(foot, text="", bg=BG, fg=MUTED, font=font(8), anchor="w")
        self.status_lbl.grid(row=7, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self.set_status(*(self._status or (None, {})))

    def _build_nowplaying(self, foot):
        box = tk.Frame(foot, bg=BG)
        box.grid(row=5, column=0, columnspan=3, sticky="w", pady=(12, 0))
        self.np_var = tk.BooleanVar(value=bool(self.s.nowplaying))
        checkbox(box, t("np.label"), self.np_var, self.toggle_nowplaying).pack(side="left")
        self.np_url = tk.StringVar(value=self.s.nowplaying.url if self.s.nowplaying else "")
        self.np_entry = tk.Entry(box, textvariable=self.np_url, state="readonly", readonlybackground=KEY, fg=WHITE,
                                 relief="flat", font=font(9), width=26)
        self.np_copy = button(box, t("np.copy"), self.copy_nowplaying)
        self.np_save = button(box, t("np.save"), self.save_nowplaying_html)
        self.np_view = button(box, t("np.preview"), lambda: webbrowser.open(self.np_url.get() + "?demo=1"))
        self._show_nowplaying_controls(bool(self.s.nowplaying))
        tk.Label(foot, text=t("np.hint"), bg=BG, fg=MUTED, font=font(8), anchor="w").grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def toggle_nowplaying(self):
        try:
            url = self.s.set_nowplaying(self.np_var.get())
        except Exception as ex:  # noqa: BLE001
            self.np_var.set(False)
            self.set_status("np.error", {"detail": str(ex)})
            return
        self.cfg["nowplaying"] = bool(url)
        self.cfg.save()
        self.np_url.set(url or "")
        self._show_nowplaying_controls(bool(url))

    def _sync_nowplaying_ui(self):
        """The overlay server starts with the session, after the widgets were built: reflect its real state."""
        url = self.s.nowplaying.url if self.s.nowplaying else ""
        self.np_var.set(bool(url))
        self.np_url.set(url)
        self._show_nowplaying_controls(bool(url))
        self._fit_window()

    def _show_nowplaying_controls(self, on):
        for w in (self.np_entry, self.np_copy, self.np_save, self.np_view):
            w.pack_forget()
        if on:
            self.np_entry.pack(side="left", padx=(12, 6), ipady=3)
            self.np_copy.pack(side="left", padx=(0, 6))
            self.np_save.pack(side="left", padx=(0, 6))
            self.np_view.pack(side="left")
        if hasattr(self, "canvas"):
            self._fit_window()

    def save_nowplaying_html(self):
        path = filedialog.asksaveasfilename(title=t("np.dialog"), defaultextension=".html", initialfile="hermetiks-nowplaying.html",
                                            filetypes=[("HTML", "*.html")])
        if path:
            shutil.copyfile(resource("overlay", "hermetiks-nowplaying.html"), path)
            self.set_status("np.saved", {"path": path})

    def copy_nowplaying(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.np_url.get())
        self.np_copy.config(text=t("np.copied"))
        self.root.after(1400, lambda: self.np_copy.config(text=t("np.copy")))

    # ---- status / language ------------------------------------------------------------------
    def set_status(self, key, params=None):
        self._status = (key, params or {})
        self.status_lbl.config(text=t(key, **(params or {})) if key else "")

    def change_language(self):
        code = next(c for c, name in LANGUAGES.items() if name == self.lang_var.get())
        self.options_changed()
        set_language(code)
        self.cfg["language"] = code
        self.cfg.save()
        self._build()
        self.select(self.selected)

    # ---- outputs & options ------------------------------------------------------------------
    def reopen_outputs(self):
        opened, errors = self.s.rebuild_outputs()
        if errors:
            self.set_status("status.output_error", {"detail": "; ".join(errors)})
        elif not opened:
            self.set_status("status.no_output")
        else:
            self.set_status("status.output", {"devices": ", ".join(opened)})

    def options_changed(self, reopen=False):
        c = self.cfg
        c["active"], c["suppress"] = self.active.get(), self.suppress.get()
        c["close_tray"], c["duck"] = self.close_tray.get(), self.duck.get()
        c["hud"] = self.hud_var.get()
        self.hud.set_enabled(c["hud"])
        self.s.set_suppress(c["suppress"])
        c["master"], c["duck_level"], c["duck_apps"] = self.master_var.get(), self.duck_level.get(), self.duck_apps.get()
        device, monitor = self.device_var.get(), self.monitor_var.get()
        c["device"] = "" if device == t("output.default") else device
        c["monitor"] = "" if monitor == t("output.none") else monitor
        self.s.apply_master()
        if self.startup.get() != c["startup"]:
            try:
                startup.set_enabled(self.startup.get())
                c["startup"] = self.startup.get()
            except Exception as ex:  # noqa: BLE001
                self.startup.set(False)
                self.set_status("status.startup_error", {"detail": str(ex)})
        c.save()
        if reopen:
            self.reopen_outputs()

    # ---- slots ------------------------------------------------------------------------------
    def refresh_button(self, slot):
        cfg = self.cfg.slot(slot)
        name = cfg["name"] or ""
        label = key_name(*self.s.slot_key(slot))
        self.buttons[slot].config(text=f"{label}\n{name[:12]}" if name else label,
                                  fg=WHITE if slot in self.s.cache else MUTED)

    def refresh_all_buttons(self):
        for slot in SLOT_IDS:
            self.refresh_button(slot)
        self.hud.refresh()
        self.stop_btn.config(text=f"{key_name(*self.s.stop_key())}  STOP")

    def select(self, slot):
        if self.selected in self.buttons:
            self.buttons[self.selected].config(bg=KEY)
        self.selected = slot
        self.buttons[slot].config(bg=KEY_HI)
        s = self.cfg.slot(slot)
        self._loading = True
        self.title_lbl.config(text=t("editor.key", name=key_name(*self.s.slot_key(slot))))
        self.name_var.set(s["name"])
        self.mode_var.set(t(f"mode.{s['mode']}"))
        self.file_lbl.config(text=self._basename(s["file"]) if s["file"] else t("editor.no_audio"))
        for key, var in self.vars.items():
            var.set(s[key])
        self._loading = False
        self.draw_wave()

    @staticmethod
    def _basename(path):
        return path.replace("\\", "/").rsplit("/", 1)[-1]

    def editor_changed(self, rerender=True):
        if self._loading:
            return
        s = self.cfg.slot(self.selected)
        s["name"] = self.name_var.get()
        s["mode"] = MODES[[t(f"mode.{m}") for m in MODES].index(self.mode_var.get())]
        for key, var in self.vars.items():
            s[key] = var.get()
        self.refresh_button(self.selected)
        self.draw_wave()
        self.cfg.save()
        if rerender:
            if self._job:
                self.root.after_cancel(self._job)
            self._job = self.root.after(250, lambda: self.s.rerender(self.selected))

    def draw_wave(self):
        c = self.wave
        c.delete("all")
        env = self.s.env.get(self.selected)
        if env is None:
            c.create_text(WAVE_W // 2, WAVE_H // 2, text=t("editor.no_audio"), fill=MUTED, font=font(9))
            return
        peak = max(float(env.max()), 1e-6)
        mid = WAVE_H // 2
        for x, v in enumerate(env):
            h = max(1, int(v / peak * (mid - 4)))
            c.create_line(x, mid - h, x, mid + h, fill=TEXT)
        s = self.cfg.slot(self.selected)
        a, b = int(WAVE_W * s["trim_in"] / 100), min(int(WAVE_W * s["trim_out"] / 100), WAVE_W - 1)
        c.create_rectangle(0, 0, a, WAVE_H, fill=BG, stipple="gray75", outline="")
        c.create_rectangle(b, 0, WAVE_W, WAVE_H, fill=BG, stipple="gray75", outline="")
        c.create_line(a, 0, a, WAVE_H, fill=WHITE)
        c.create_line(b, 0, b, WAVE_H, fill=WHITE)

    def pick_file(self):
        exts = " ".join("*" + e for e in importer.AUDIO_EXT)
        path = filedialog.askopenfilename(title=t("dlg.pick_audio"),
                                          filetypes=[(t("dlg.audio_files"), exts), (t("dlg.all_files"), "*.*")])
        if path:
            self.s.add_file(self.selected, path)
            self.set_status("status.loading")
            self.select(self.selected)

    def import_url(self):
        url = simpledialog.askstring("HERMETIKS", t("dlg.url_prompt"), parent=self.root)
        if url and url.strip():
            self.set_status("status.downloading")
            self.s.import_url(self.selected, url.strip())

    def clear_slot(self):
        self.s.clear_slot(self.selected)
        self.refresh_button(self.selected)
        self.select(self.selected)

    # ---- keys ---------------------------------------------------------------------------------
    def begin_capture(self, target):
        self.s.start_capture(target)
        self.set_status("status.press_key")

    def reset_key(self):
        self.s.reset_key(self.selected)
        self.refresh_all_buttons()
        self.select(self.selected)

    # ---- profiles ---------------------------------------------------------------------------
    def _reload_profiles(self):
        self.profile_box.config(values=self.cfg.profile_names)
        self.profile_var.set(self.cfg.profile)

    def switch_profile(self, name):
        self.s.switch_profile(name)
        self.refresh_all_buttons()
        self.select(self.selected)

    def new_profile(self):
        name = simpledialog.askstring("HERMETIKS", t("profile.new_prompt"), parent=self.root)
        if name and self.cfg.add_profile(name):
            self._reload_profiles()
            self.switch_profile(name.strip())
            self._reload_profiles()

    def rename_profile(self):
        name = simpledialog.askstring("HERMETIKS", t("profile.rename_prompt"), initialvalue=self.cfg.profile,
                                      parent=self.root)
        if name and self.cfg.rename_profile(name):
            self.cfg.save()
            self._reload_profiles()

    def delete_profile(self):
        if len(self.cfg.profile_names) < 2:
            messagebox.showinfo("HERMETIKS", t("profile.min_one"))
        elif messagebox.askyesno("HERMETIKS", t("profile.delete_confirm", name=self.cfg.profile)):
            self.cfg.delete_profile()
            self._reload_profiles()
            self.switch_profile(self.cfg.profile)

    # ---- backend events ---------------------------------------------------------------------
    def poll(self):
        if not self._alive:
            return
        try:
            while True:
                event = self.s.events.get_nowait()
                if self.handle(event):
                    return
        except queue.Empty:
            pass
        peak = min(1.0, max((o.peak for o in self.s.outs), default=0.0))
        self.meter.delete("all")
        self.meter.create_rectangle(0, 0, int(110 * peak), 6, fill=WHITE, outline="")
        self.root.after(40, self.poll)

    def handle(self, event):
        kind = event[0]
        if kind == "flash":
            slot = event[1]
            self.hud.flash(slot)
            b = self.buttons[slot]
            b.config(bg=WHITE, fg=BG)
            self.root.after(120, lambda: b.config(bg=KEY_HI if slot == self.selected else KEY,
                                                  fg=WHITE if slot in self.s.cache else MUTED))
        elif kind == "refresh":
            self.refresh_button(event[1])
            self.hud.refresh()
            if event[1] == self.selected:
                self.draw_wave()
            self.set_status(None)
        elif kind == "status":
            self.set_status(event[1], event[2])
        elif kind == "imported":
            self.s.assign_file(event[1], event[2], event[3])
            self.set_status("status.loading")
            if event[1] == self.selected:
                self.select(event[1])
        elif kind == "captured":
            self.s.apply_captured(event[1], event[2])
            self.set_status(None)
            self.refresh_all_buttons()
            self.select(self.selected)
        elif kind == "show":
            log.info("show event from tray")
            self.root.deiconify()
            self.root.lift()
        elif kind == "toggle":
            self.active.set(not self.active.get())
            self.options_changed()
        elif kind == "quit":
            log.info("quit event from tray")
            self.quit()
            return True
        return False

    # ---- window lifecycle ---------------------------------------------------------------------
    def on_close(self):
        log.info("window close requested (close_tray=%s)", self.cfg["close_tray"])
        if self.cfg["close_tray"] and self.tray:
            self.root.withdraw()
        else:
            self.quit()

    def quit(self):
        log.info("quit")
        self._alive = False
        self.hud.destroy()
        self.s.shutdown()
        if self.tray:
            self.tray.stop()
        self.root.destroy()
