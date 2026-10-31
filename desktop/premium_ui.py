import math
import os
import sys
import time
import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox
from zoneinfo import ZoneInfo

from zishan_clock import (
    DAYLIGHT_EVENTS, EVENTS, HIJRI_LANGUAGES, HIJRI_SOURCES, METHODS, PRAYERS, bangla_date, cache_prayer_schedule,
    calculate_prayers, ensure_prayer_events,
    load_settings, next_general_alarm, parse_clock_time, prayer_event_time,
    save_settings, scheduled_prayer_events, play_alarm_sound, play_focus_sound, stop_alarm_sound,
    stop_focus_sound, sync_hijri_date, sync_prayer_schedule, check_internet, winsound,
)


BG = "#071015"
SIDEBAR = "#0b1518"
CARD = "#102129"
CARD_ALT = "#0c1a1e"
CARD_ACTIVE = "#123b36"
EMERALD = "#00e6a8"
EMERALD_DARK = "#0f6e54"
GOLD = "#ffd166"
TEXT = "#eff8f3"
MUTED = "#8ea7a0"
LINE = "#142a30"
CARD_HOVER = "#142a32"
DANGER = "#ff6b6b"


class PremiumClockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        ensure_prayer_events(self.settings)
        self.title("Zishan Islamic Clock")
        self.geometry(self.settings.get("window_geometry", "1180x760"))
        self.minsize(940, 640)
        self.after_idle(self._maximize_window)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._close_app)
        self.bind("<Escape>", lambda event: self.attributes("-fullscreen", False))
        self.page = "Dashboard"
        self.stopwatch_start = None
        self.stopwatch_elapsed = 0.0
        self.stopwatch_laps = []
        self._stopwatch_after_id = None
        self.timer_deadline = None
        self.timer_remaining = 0
        self.timer_running = False
        self.study_deadline = None
        self.study_running = False
        if getattr(self, "focus_card", None):
            self.focus_card.configure(bg=CARD, highlightbackground=LINE)
        self.study_phase = "Study"
        if getattr(self, "focus_card", None):
            self.focus_card.configure(bg=CARD, highlightbackground=LINE)
        self.study_streak = 0
        self.study_today_seconds = 0.0
        self.study_sessions_completed = 0
        self.study_accounted_at = None
        self._load_focus_stats()
        self._study_after_id = None
        self.alarm_stop = False
        self._alarm_after_id = None
        self._hijri_sync_running = False
        self._data_sync_running = False
        self._last_maintenance_key = None
        self._tools_canvas = None
        self._configure_fonts()
        self._build_shell()
        self.bind("<Control-Shift-T>", lambda event: self._increment_tasbih())
        self._show_page("Dashboard")
        self._start_alarm_monitor()
        self._tick()

    def _configure_fonts(self):
        self.font_body = ("Segoe UI Variable", 10)
        self.font_small = ("Segoe UI Variable", 9)
        self.font_title = ("Segoe UI Variable Semibold", 18)
        self.font_clock = ("Segoe UI Semibold", 58)
        self.font_display = ("Segoe UI Semibold", 36)

    def _maximize_window(self):
        self.state("zoomed")

    def _close_app(self):
        stop_focus_sound()
        self._save_note_now()
        self.settings["window_geometry"] = self.geometry()
        save_settings(self.settings)
        self.destroy()

    def _build_shell(self):
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=18, pady=(28, 36))
        tk.Label(brand, text="◒", fg=EMERALD, bg=SIDEBAR, font=("Segoe UI", 28)).pack(side="left")
        tk.Label(brand, text="ZISHAN\nISLAMIC CLOCK", fg=TEXT, bg=SIDEBAR,
                 font=("Segoe UI Semibold", 11), justify="left").pack(side="left", padx=8)
        self.nav_buttons = {}
        for name, icon in (("Dashboard", "⌂"), ("Prayer alarms", "◷"), ("General alarms", "◴"),
                           ("Tools", "◌"), ("Settings", "⚙"), ("About", "i"), ("AI Quran", "▣")):
            self.nav_buttons[name] = self._nav_button(name, icon)
        tk.Frame(self.sidebar, bg=SIDEBAR).pack(fill="both", expand=True)
        tk.Label(self.sidebar, text="OFFLINE CALCULATION\nNo ads · No tracking", fg=MUTED, bg=SIDEBAR,
                 font=self.font_small, justify="left").pack(anchor="w", padx=24, pady=(0, 24))
        self.main = tk.Frame(self, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(self.main, bg=BG)
        self.header.pack(fill="x", padx=34, pady=(26, 12))
        self.page_title = tk.Label(self.header, text="", fg=TEXT, bg=BG, font=self.font_title)
        self.page_title.pack(side="left")
        self.header_meta = tk.Label(self.header, text="", fg=MUTED, bg=BG, font=self.font_small)
        self.header_meta.pack(side="right", pady=6)
        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=34, pady=(0, 26))

    def _nav_button(self, name, icon):
        button = tk.Button(self.sidebar, text=f"  {icon}   {name}", anchor="w", relief="flat",
                           bd=0, cursor="hand2", font=self.font_body, padx=14, pady=11,
                           bg=SIDEBAR, fg=MUTED, activebackground=CARD_ALT,
                           highlightthickness=1, highlightbackground=SIDEBAR,
                           activeforeground=TEXT, command=lambda: self._show_page(name))
        button.pack(fill="x", padx=14, pady=2)
        button.bind("<Enter>", lambda event, item=button: item.configure(bg=CARD_ACTIVE, fg=TEXT))
        button.bind("<Leave>", lambda event, item=button: item.configure(
            bg=CARD_ALT if item is self.nav_buttons.get(self.page) else SIDEBAR,
            fg=TEXT if item is self.nav_buttons.get(self.page) else MUTED))
        return button

    def _clear(self):
        if getattr(self, "_settings_canvas", None) is not None:
            self.unbind_all("<MouseWheel>")
            self._settings_canvas = None
        for child in self.content.winfo_children():
            child.destroy()
        self.stopwatch_label = None
        self.stopwatch_laps_label = None
        self.study_label = None
        self.study_progress_label = None
        self.study_phase_label = None
        self.tasbih_label = None
        self.tasbih_daily_label = None
        self.notes_text = None
        self.note_saved_label = None
        self.focus_ring = None
        if getattr(self, "_tools_canvas", None) is not None:
            self.unbind_all("<MouseWheel>")
            self._tools_canvas = None
        self.focus_card = None

    def _show_page(self, name):
        self.page = name
        self._clear()
        self.page_title.configure(text=name)
        for item, button in self.nav_buttons.items():
            button.configure(bg=CARD_ALT if item == name else SIDEBAR,
                             fg=TEXT if item == name else MUTED,
                             highlightbackground=EMERALD if item == name else SIDEBAR)
        if name == "Dashboard":
            self._dashboard()
        elif name == "Prayer alarms":
            self._prayer_alarms()
        elif name == "General alarms":
            self._general_alarms()
        elif name == "Tools":
            self._tools()
        elif name == "Settings":
            self._settings()
        elif name == "AI Quran":
            self._quran()
        else:
            self._about()

    def _card(self, parent, title=None, accent=False):
        frame = tk.Frame(parent, bg=CARD if not accent else CARD_ACTIVE,
                         highlightbackground=EMERALD_DARK if accent else LINE,
                         highlightthickness=1, bd=0)
        frame.bind("<Enter>", lambda event, item=frame: item.configure(highlightbackground=EMERALD))
        frame.bind("<Leave>", lambda event, item=frame, accent=accent: item.configure(
            highlightbackground=EMERALD_DARK if accent else LINE))
        if title:
            tk.Label(frame, text=title.upper(), fg=GOLD if accent else MUTED, bg=frame["bg"],
                     font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=18, pady=(15, 8))
        return frame

    def _tools_scroll_host(self):
        wrapper = tk.Frame(self.content, bg=BG)
        wrapper.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrapper, bg=BG, highlightthickness=0, bd=0)
        inner = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.pack(fill="both", expand=True)
        inner.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        canvas.bind("<Enter>", lambda event: canvas.focus_set())
        self._tools_wheel = lambda event: canvas.yview_scroll(int(-event.delta / 120), "units")
        self.bind_all("<MouseWheel>", self._tools_wheel)
        self._tools_canvas = canvas
        return inner

    def _label(self, parent, text, font=None, color=TEXT, **kwargs):
        return tk.Label(parent, text=text, fg=color, bg=parent["bg"], font=font or self.font_body, **kwargs)

    def _button(self, parent, text, command, primary=False):
        button = tk.Button(parent, text=text, command=command, relief="flat", bd=0, cursor="hand2",
                         font=("Segoe UI Semibold", 10), padx=14, pady=9,
                         bg=EMERALD if primary else CARD_ALT, fg=BG if primary else TEXT,
                         activebackground="#32e5a9" if primary else CARD_ACTIVE,
                         activeforeground=BG if primary else TEXT)
        button.bind("<Enter>", lambda event: button.configure(
            bg="#42f3bd" if primary else CARD_ACTIVE))
        button.bind("<Leave>", lambda event: button.configure(
            bg=EMERALD if primary else CARD_ALT))
        return button

    def _dashboard(self):
        self.header_meta.configure(text=f"{self.settings.get('city', 'Manual location')}  ·  local time")
        hero = self._card(self.content, accent=True)
        hero.pack(fill="x", pady=(0, 18))
        left = tk.Frame(hero, bg=CARD_ACTIVE)
        left.pack(side="left", fill="both", expand=True, padx=30, pady=24)
        self._label(left, "LOCAL TIME", self.font_small, GOLD).pack(anchor="w")
        self.digital = self._label(left, "--:--:-- AM", ("Segoe UI Variable Semibold", 68), TEXT)
        self.digital.pack(anchor="w", pady=(2, 4))
        self.date_line = self._label(left, "", ("Segoe UI Variable", 17), MUTED)
        self.date_line.pack(anchor="w")
        self.bangla_line = self._label(left, "", ("Segoe UI Variable", 17), TEXT)
        self.bangla_line.pack(anchor="w", pady=(4, 0))
        self.hijri_line = self._label(left, "", ("Segoe UI", 17), TEXT)
        self.hijri_line.pack(anchor="w", pady=(4, 0))
        self.hijri_source_line = self._label(left, "", self.font_small, MUTED)
        self.hijri_source_line.pack(anchor="w", pady=(4, 0))
        right = tk.Frame(hero, bg=CARD_ACTIVE)
        right.pack(side="right", padx=28, pady=24)
        self.next_title = self._label(right, "NEXT PRAYER", self.font_small, GOLD)
        self.next_title.pack(anchor="e")
        self.next_line = self._label(right, "🕌 Dhuhr", ("Segoe UI Variable Semibold", 25), TEXT)
        self.next_line.pack(anchor="e", pady=(5, 0))
        self.countdown_line = self._label(right, "00:00:00 remaining", ("Segoe UI Variable Semibold", 32), EMERALD)
        self.countdown_line.pack(anchor="e", pady=(4, 12))
        self.current_prayer_line = self._label(right, "CURRENT PRAYER  —", self.font_small, MUTED)
        self.current_prayer_line.pack(anchor="e", pady=(8, 0))
        self.analog = tk.Canvas(right, width=170, height=170, bg=CARD_ACTIVE, highlightthickness=0)
        self.analog.pack(anchor="e", pady=(18, 0))

        self._label(self.content, "TODAY'S PRAYER TIMES", self.font_small, MUTED).pack(anchor="w", pady=(6, 9))
        self.prayer_grid = tk.Frame(self.content, bg=BG)
        self.prayer_grid.pack(fill="x")
        for index, name in enumerate(DAYLIGHT_EVENTS):
            card = self._card(self.prayer_grid)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 5, 5))
            self.prayer_grid.grid_columnconfigure(index, weight=1)
            self._label(card, name, ("Segoe UI Variable Semibold", 11), GOLD).pack(anchor="w", padx=14, pady=(14, 4))
            value = self._label(card, "--:--", ("Segoe UI Variable Semibold", 20), TEXT)
            value.pack(anchor="w", padx=14, pady=(0, 4))
            state = self._label(card, "CALCULATED", self.font_small, MUTED)
            state.pack(anchor="w", padx=14, pady=(0, 14))
            card.value_label, card.state_label, card.prayer_name = value, state, name

        timeline = self._card(self.content, "Prayer timeline")
        timeline.pack(fill="x", pady=(18, 0))
        self.timeline = tk.Canvas(timeline, height=82, bg=CARD, highlightthickness=0)
        self.timeline.pack(fill="x", padx=20, pady=(0, 14))

        calendar = self._card(self.content, "Islamic calendar")
        calendar.pack(fill="x", pady=(14, 0))
        self.calendar_gregorian = self._label(calendar, "", ("Segoe UI Variable Semibold", 16), TEXT)
        self.calendar_gregorian.pack(side="left", padx=18, pady=16)
        self.calendar_bangla = self._label(calendar, "", ("Segoe UI", 16), TEXT)
        self.calendar_bangla.pack(side="left", padx=18, pady=16)
        self.calendar_hijri = self._label(calendar, "", ("Segoe UI", 16), TEXT)
        self.calendar_hijri.pack(side="left", padx=18, pady=16)

        actions = tk.Frame(self.content, bg=BG)
        actions.pack(fill="x", pady=18)
        for text, command in (("Prayer alarms", lambda: self._show_page("Prayer alarms")),
                              ("General alarms", lambda: self._show_page("General alarms")),
                              ("Timer & stopwatch", lambda: self._show_page("Tools")),
                              ("Settings", lambda: self._show_page("Settings"))):
            self._button(actions, text, command, primary=text == "Prayer alarms").pack(side="left", padx=(0, 8))
        self._button(actions, "⛶", self._toggle_fullscreen, primary=True).pack(side="left", padx=(8, 0))
        self._refresh_hijri(datetime.now(ZoneInfo(self.settings["timezone"])).date())
        self._refresh_prayer_cache(datetime.now(ZoneInfo(self.settings["timezone"])).date())

    def _dashboard_update(self, now):
        if not hasattr(self, "digital") or self.page != "Dashboard":
            return
        self.digital.configure(text=now.strftime("%I:%M:%S %p").lstrip("0"))
        self.date_line.configure(text=now.strftime("%A, %d %B %Y"))
        self._draw_analog(now, self.analog, 62)
        local_now = datetime.now(ZoneInfo(self.settings["timezone"]))
        prayers = self._get_cached_or_calculated_prayers(local_now.date())
        future = [(value, name) for name, value in prayers.items() if value and value > local_now]
        if future:
            target, name = min(future)
            remaining = target - local_now
            self.next_line.configure(text=f"🕌  {name}")
            self.countdown_line.configure(text=f"{str(remaining).split('.')[0]} remaining")
        else:
            self.next_line.configure(text="🕌  Tomorrow")
            self.countdown_line.configure(text="Next day calculated at midnight")
        self.current_prayer_line.configure(
            text=f"CURRENT PRAYER  {self._current_prayer_name(prayers, local_now) or '—'}")
        active = None
        ordered = [(name, value) for name, value in prayers.items()
                   if value and name in PRAYERS]
        for index, (name, value) in enumerate(ordered):
            next_value = ordered[index + 1][1] if index + 1 < len(ordered) else None
            if value <= local_now and (next_value is None or local_now < next_value):
                active = name
        for card in self.prayer_grid.winfo_children():
            value = prayers.get(card.prayer_name)
            is_active = card.prayer_name == active or (not active and future and card.prayer_name == future[0][1])
            card.value_label.configure(text=value.strftime("%I:%M %p").lstrip("0") if value else "Unavailable")
            card.state_label.configure(text="NOW" if is_active else "CALCULATED",
                                       fg=EMERALD if is_active else MUTED)
            card.configure(bg=CARD_HOVER if is_active else CARD,
                           highlightbackground=EMERALD if is_active else LINE)
            for child in card.winfo_children():
                child.configure(bg=CARD_HOVER if is_active else CARD)
        bangla = bangla_date(local_now.date())
        self.bangla_line.configure(text=f"{bangla['day']} {bangla['month_name']} {bangla['year']} বঙ্গাব্দ")
        self.calendar_gregorian.configure(text=local_now.strftime("%A, %d %B %Y"))
        self.calendar_bangla.configure(text=f"{bangla['day']} {bangla['month_name']} {bangla['year']} বঙ্গাব্দ")
        if getattr(self, "_hijri_day", None) != local_now.date():
            self._hijri_day = local_now.date()
            self._refresh_hijri(self._hijri_day)
        self._draw_timeline(prayers, local_now, active)
        self._run_daily_maintenance(local_now)

    def _get_cached_or_calculated_prayers(self, day):
        online = self.settings.get("prayer_online_cache", {})
        if (self.settings.get("prayer_sync_status") == "Prayer: Online reference"
                and online.get("date") == day.isoformat()):
            try:
                return {name: datetime.fromisoformat(value) if value else None
                        for name, value in online["times"].items()}
            except (KeyError, TypeError, ValueError):
                pass
        cached = self.settings.get("prayer_cache", {}).get(day.isoformat())
        if cached:
            try:
                return {name: datetime.fromisoformat(value) if value else None
                        for name, value in cached.items()}
            except (TypeError, ValueError):
                pass
        prayers = cache_prayer_schedule(day, self.settings)
        save_settings(self.settings)
        return prayers

    @staticmethod
    def _current_prayer_name(prayers, now):
        ordered = [(name, value) for name, value in prayers.items()
                   if value and name in PRAYERS]
        for index, (name, value) in enumerate(ordered):
            following = ordered[index + 1][1] if index + 1 < len(ordered) else None
            if value <= now and (following is None or now < following):
                return name
        return None

    def _refresh_prayer_cache(self, day):
        cache_prayer_schedule(day, self.settings)
        save_settings(self.settings)

    def _run_daily_maintenance(self, local_now):
        key = local_now.strftime("%Y-%m-%d-%H")
        if self._last_maintenance_key == key:
            return
        self._last_maintenance_key = key
        if local_now.hour == 0 and local_now.minute >= 1:
            self._refresh_prayer_cache(local_now.date())
        if local_now.hour >= 20 and not self._data_sync_running:
            self._data_sync_running = True
            threading.Thread(target=self._sync_daily_data,
                             args=(local_now.date(),), daemon=True).start()

    def _sync_daily_data(self, day):
        source = self.settings.get("hijri_source", "Bangladesh Official")
        result = sync_hijri_date(day, source)
        try:
            if result:
                self.settings["hijri_cache"] = result
                if result.get("source") == "Online reference fallback":
                    self.settings["hijri_sync_status"] = (
                        f"Synced online: reference fallback ({source} endpoint unavailable)")
                else:
                    self.settings["hijri_sync_status"] = f"Synced: {source}"
            else:
                self.settings["hijri_sync_status"] = "Offline Calculated"
            cache_prayer_schedule(day, self.settings)
            save_settings(self.settings)
        finally:
            self.after(0, self._finish_daily_data_sync)

    def _finish_daily_data_sync(self):
        self._data_sync_running = False
        if self.page == "Dashboard":
            self._refresh_hijri(datetime.now(ZoneInfo(self.settings["timezone"])).date())

    def _refresh_hijri(self, day):
        from zishan_clock import offline_hijri
        cached = self.settings.get("hijri_cache", {})
        source = self.settings.get("hijri_source", "Bangladesh Official")
        current = (cached if cached.get("synced_date") == day.isoformat()
                   and (cached.get("source") == source
                        or cached.get("requested_source") == source
                        or cached.get("source") == "Online reference fallback")
                   else offline_hijri(day))
        self._set_hijri_display(current)
        if not self._hijri_sync_running:
            self._hijri_sync_running = True
            threading.Thread(target=self._sync_hijri_worker, args=(day, source), daemon=True).start()

    def _sync_hijri_worker(self, day, source):
        result = sync_hijri_date(day, source)
        self.after(0, lambda: self._finish_hijri_sync(day, result))

    def _finish_hijri_sync(self, day, result):
        self._hijri_sync_running = False
        if result:
            self.settings["hijri_cache"] = result
            save_settings(self.settings)
            if self.page == "Dashboard":
                self._set_hijri_display(result)

    def _set_hijri_display(self, value):
        english = f"{value['day']} {value['month_name']} {value['year']} AH"
        arabic = f"{value['day']} {value.get('arabic_month', '')} {value['year']} هـ"
        language = self.settings.get("hijri_language", "English")
        text = english if language == "English" else arabic if language == "Arabic" else f"{english}\n{arabic}"
        source = self.settings.get("hijri_sync_status") or value.get("source", "Offline Calculated")
        self.hijri_line.configure(text=text)
        self.hijri_source_line.configure(text=source)
        if hasattr(self, "calendar_hijri"):
            self.calendar_hijri.configure(text=text)

    def _draw_timeline(self, prayers, now, active):
        if not hasattr(self, "timeline"):
            return
        canvas = self.timeline
        canvas.delete("all")
        width = max(canvas.winfo_width(), 600)
        points = []
        valid = [(name, value) for name, value in prayers.items() if value]
        if not valid:
            return
        left, right = 42, width - 42
        span = max(1, (valid[-1][1] - valid[0][1]).total_seconds())
        canvas.create_line(left, 36, right, 36, fill=LINE, width=5)
        for index, (name, value) in enumerate(valid):
            x = left + (right - left) * index / max(1, len(valid) - 1)
            points.append((name, x))
            passed = now >= value
            canvas.create_oval(x - 6, 30, x + 6, 42, fill=EMERALD if passed else CARD_ALT,
                               outline=EMERALD if passed else MUTED, width=2)
            canvas.create_text(x, 15, text=name, fill=TEXT if name == active else MUTED,
                               font=("Segoe UI Variable Semibold", 9))
            canvas.create_text(x, 61, text=value.strftime("%I:%M").lstrip("0"), fill=TEXT,
                               font=("Segoe UI Variable", 9))

    def _prayer_alarms(self):
        self._label(self.content, "Configure Azan and prayer reminders independently. Offset mode follows each day's calculated time.", color=MUTED).pack(anchor="w", pady=(0, 16))
        ensure_prayer_events(self.settings)
        headers = self._card(self.content)
        headers.pack(fill="x", pady=(0, 4))
        for text, width in (("Prayer", 12), ("Azan", 10), ("Mode", 12), ("Offset / time", 14), ("Reminder", 12), ("Mode", 12), ("Offset / time", 14)):
            self._label(headers, text, color=MUTED, width=width, anchor="w").pack(side="left", padx=5, pady=8)
        for name in PRAYERS:
            row = self._card(self.content)
            row.pack(fill="x", pady=5)
            prayers = calculate_prayers(datetime.now().date(), self.settings)
            value = prayers[name]
            self._label(row, name, ("Segoe UI Semibold", 11), GOLD, width=12, anchor="w").pack(side="left", padx=5)
            self._label(row, value.strftime("%I:%M %p").lstrip("0") if value else "Unavailable", color=MUTED, width=10, anchor="w").pack(side="left", padx=5)
            for event_name in EVENTS:
                event = self.settings["prayer_events"][name][event_name]
                enabled = tk.BooleanVar(value=event["enabled"])
                tk.Checkbutton(row, variable=enabled, command=lambda n=name, e=event_name, v=enabled: self._set_prayer_event(n, e, "enabled", v.get()),
                               bg=CARD, fg=TEXT, selectcolor=CARD_ALT, activebackground=CARD,
                               activeforeground=TEXT).pack(side="left", padx=5)
                mode = tk.StringVar(value=event["mode"])
                menu = tk.OptionMenu(row, mode, "offset", "fixed",
                                     command=lambda value, n=name, e=event_name: self._set_prayer_event(n, e, "mode", value))
                menu.configure(bg=CARD_ALT, fg=TEXT, activebackground=CARD_ACTIVE, activeforeground=TEXT, relief="flat", bd=0, highlightthickness=0, width=8)
                menu.pack(side="left", padx=5)
                field_value = str(event["offset"]) if event["mode"] == "offset" else event["time"]
                field = self._entry(row, field_value)
                field.configure(width=12)
                field.pack(side="left", padx=5)
                self._button(row, "Save", lambda n=name, e=event_name, m=mode, f=field: self._save_prayer_event(n, e, m, f)).pack(side="left", padx=4)

    def _set_prayer_event(self, name, event_name, key, value):
        ensure_prayer_events(self.settings)
        self.settings["prayer_events"][name][event_name][key] = value
        if event_name == "azan":
            self.settings["prayer_alarms"][name] = bool(value) if key == "enabled" else self.settings["prayer_events"][name]["azan"]["enabled"]
        save_settings(self.settings)

    def _save_prayer_event(self, name, event_name, mode, field):
        try:
            event = self.settings["prayer_events"][name][event_name]
            event["mode"] = mode.get()
            if event["mode"] == "offset":
                value = int(field.get())
                if not -720 <= value <= 720:
                    raise ValueError
                event["offset"] = value
            else:
                hour, minute = parse_clock_time(field.get())
                event["time"] = f"{hour:02d}:{minute:02d}"
            save_settings(self.settings)
            self._show_page("Prayer alarms")
        except (ValueError, KeyError):
            messagebox.showerror("Prayer event", "Use an offset from -720 to 720, or a valid fixed HH:MM time.")

    def _general_alarms(self):
        self._label(self.content, "Local alarms run while this app is open. Choose specific weekdays or leave them empty for a one-time alarm.", color=MUTED).pack(anchor="w", pady=(0, 16))
        form = self._card(self.content, "Create or update")
        form.pack(fill="x", pady=(0, 14))
        self.editing_general_index = None
        self.general_hour, self.general_minute, self.general_ampm = self._time_picker(form, "07:00")
        self.general_time_frame = form
        self.general_label = self._entry(form, "Alarm")
        self.general_label.pack(side="left", padx=5, pady=16)
        self.general_repeat = []
        for day, short in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            var = tk.BooleanVar(value=False)
            self.general_repeat.append(var)
            tk.Checkbutton(form, text=short, variable=var, bg=CARD, fg=TEXT, selectcolor=CARD_ALT,
                           activebackground=CARD, activeforeground=TEXT).pack(side="left", padx=1)
        self.general_save_button = self._button(form, "Add alarm", self._save_general, True)
        self.general_save_button.pack(side="right", padx=12, pady=10)
        self.general_status = self._label(self.content, "", color=MUTED)
        self.general_status.pack(anchor="w")
        self._render_general_alarms()

    def _general_text(self):
        alarms = self.settings.get("general_alarms", [])
        if not alarms:
            return "No general alarm saved."
        return f"{len(alarms)} alarm(s) saved."

    @staticmethod
    def _format_ampm(value):
        hour, minute = parse_clock_time(value)
        return f"{(hour - 1) % 12 + 1}:{minute:02d} {'AM' if hour < 12 else 'PM'}"

    def _save_general(self):
        try:
            hour = int(self.general_hour.get()) % 12
            if self.general_ampm.get() == "PM":
                hour += 12
            minute = int(self.general_minute.get())
            if minute not in range(60):
                raise ValueError
            repeat = [index for index, value in enumerate(self.general_repeat) if value.get()]
            alarm = {
                "time": f"{hour:02d}:{minute:02d}", "label": self.general_label.get().strip() or "Alarm",
                "enabled": True, "repeat": repeat, "snooze": self.settings["snooze"],
            }
            alarms = self.settings.setdefault("general_alarms", [])
            if self.editing_general_index is None:
                alarms.append(alarm)
            else:
                alarm["enabled"] = bool(alarms[self.editing_general_index].get("enabled", True))
                alarms[self.editing_general_index] = alarm
            save_settings(self.settings)
            self._show_page("General alarms")
        except ValueError:
            messagebox.showerror("General alarm", "Choose a valid hour, minute, and AM/PM.")

    def _render_general_alarms(self):
        for index, alarm in enumerate(self.settings.get("general_alarms", [])):
            row = self._card(self.content)
            row.pack(fill="x", pady=4)
            repeat = alarm.get("repeat", [])
            repeat_text = "Once" if not repeat else " · ".join(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[day] for day in repeat)
            next_time = next_general_alarm(alarm, datetime.now())
            self._label(row, f"{alarm.get('label', 'Alarm')}  ·  {self._format_ampm(alarm.get('time', '00:00'))}  ·  {repeat_text}", color=TEXT).pack(side="left", padx=16, pady=12)
            self._label(row, f"Next: {next_time.strftime('%a %d %b %H:%M') if next_time else 'disabled'}", color=MUTED).pack(side="left", padx=10)
            enabled = tk.BooleanVar(value=bool(alarm.get("enabled")))
            tk.Checkbutton(row, text="Enabled", variable=enabled, command=lambda i=index, v=enabled: self._toggle_general(i, v.get()),
                           bg=CARD, fg=TEXT, selectcolor=CARD_ALT, activebackground=CARD, activeforeground=TEXT).pack(side="right", padx=4)
            self._button(row, "Delete", lambda i=index: self._delete_general(i)).pack(side="right", padx=4)
            self._button(row, "Edit", lambda i=index: self._edit_general(i)).pack(side="right", padx=4)

    def _edit_general(self, index):
        alarm = self.settings["general_alarms"][index]
        self.editing_general_index = index
        hour, minute = parse_clock_time(alarm.get("time", "07:00"))
        self.general_hour.set(str((hour - 1) % 12 + 1))
        self.general_minute.set(f"{minute:02d}")
        self.general_ampm.set("AM" if hour < 12 else "PM")
        self.general_label.delete(0, "end")
        self.general_label.insert(0, alarm.get("label", "Alarm"))
        repeat = set(alarm.get("repeat", []))
        for day, variable in enumerate(self.general_repeat):
            variable.set(day in repeat)
        self.general_save_button.configure(text="Save changes")
        self.general_hour.focus_set()

    def _toggle_general(self, index, enabled):
        self.settings["general_alarms"][index]["enabled"] = enabled
        save_settings(self.settings)

    def _delete_general(self, index):
        if messagebox.askyesno("Delete alarm", "Delete this alarm?"):
            del self.settings["general_alarms"][index]
            save_settings(self.settings)
            self._show_page("General alarms")

    def _settings(self):
        scroller = tk.Frame(self.content, bg=BG)
        scroller.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroller, bg=BG, highlightthickness=0, bd=0)
        inner = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.pack(fill="both", expand=True)
        inner.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))

        def scroll(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")

        canvas.bind_all("<MouseWheel>", scroll)
        self._settings_canvas = canvas
        self._settings_mousewheel = scroll
        self._label(inner, "Location and calculation", self.font_title).pack(anchor="w", pady=(0, 12))
        panel = self._card(inner)
        panel.pack(fill="x")
        self.setting_entries = {}
        for label, key in (("Latitude", "latitude"), ("Longitude", "longitude"), ("Time zone", "timezone")):
            line = tk.Frame(panel, bg=CARD)
            line.pack(fill="x", padx=18, pady=7)
            self._label(line, label, color=MUTED, width=16, anchor="w").pack(side="left")
            entry = self._entry(line, str(self.settings[key]))
            entry.pack(side="left", fill="x", expand=True)
            self.setting_entries[key] = entry
        city_line = tk.Frame(panel, bg=CARD)
        city_line.pack(fill="x", padx=18, pady=7)
        self._label(city_line, "City / label", color=MUTED, width=16, anchor="w").pack(side="left")
        city_entry = self._entry(city_line, self.settings.get("city", "Chattogram, Bangladesh"))
        city_entry.pack(side="left", fill="x", expand=True)
        self.setting_entries["city"] = city_entry
        self.method = self._combo(panel, list(METHODS), self.settings["method"])
        self.method.pack(fill="x", padx=18, pady=7)
        self.asr = self._combo(panel, ["Hanafi", "Shafi'i"], self.settings["asr"])
        self.asr.pack(fill="x", padx=18, pady=7)
        self.high_latitude = self._combo(panel, ["Middle of the night", "Seventh of the night", "Twilight angle"],
                                         self.settings.get("high_latitude", "Middle of the night"))
        self.high_latitude.pack(fill="x", padx=18, pady=7)
        hijri_panel = self._card(panel, "Hijri calendar source")
        hijri_panel.pack(fill="x", padx=18, pady=8)
        self.hijri_source = self._combo(hijri_panel, list(HIJRI_SOURCES),
                                        self.settings.get("hijri_source", HIJRI_SOURCES[0]))
        self.hijri_source.pack(side="left", padx=12, pady=10)
        self._label(hijri_panel, "Saudi source syncs online when available; other sources use the cached/local fallback.",
                    self.font_small, MUTED).pack(side="left", padx=8)
        language_panel = self._card(panel, "Hijri language")
        language_panel.pack(fill="x", padx=18, pady=(0, 8))
        self.hijri_language = self._combo(language_panel, list(HIJRI_LANGUAGES),
                                           self.settings.get("hijri_language", "English"))
        self.hijri_language.pack(side="left", padx=12, pady=10)
        self._label(language_panel, "English is the default; Both adds the Arabic line.",
                    self.font_small, MUTED).pack(side="left", padx=8)
        adjustments = self._card(panel, "Minute adjustments")
        adjustments.pack(fill="x", padx=18, pady=8)
        self.adjustment_entries = {}
        for prayer in PRAYERS:
            line = tk.Frame(adjustments, bg=CARD)
            line.pack(side="left", padx=4, pady=8)
            self._label(line, prayer[:3], color=MUTED).pack()
            field = self._entry(line, str(self.settings.get("adjustments", {}).get(prayer, 0)))
            field.configure(width=4, justify="center")
            field.pack()
            self.adjustment_entries[prayer] = field
        self._button(panel, "Save calculation settings", self._save_calc, True).pack(anchor="e", padx=18, pady=16)
        sync_panel = self._card(inner, "Online sync")
        sync_panel.pack(fill="x", pady=(0, 16))
        sync_text = (
            "Uses the internet only for the selected Hijri reference and coordinate-based prayer "
            "reference. Local cached/calculated data remains available offline."
        )
        sync_info = tk.Frame(sync_panel, bg=CARD)
        sync_info.pack(side="left", fill="x", expand=True, padx=18, pady=10)
        self._label(sync_info, sync_text, self.font_small, MUTED,
                    wraplength=560, justify="left").pack(anchor="w")
        self.sync_status_label = self._label(
            sync_info, self._sync_status_text(),
            self.font_small, GOLD, wraplength=560, justify="left")
        self.sync_status_label.pack(anchor="w", pady=(5, 0))
        self._button(sync_panel, "Sync now", self._sync_now, True).pack(side="right", padx=18, pady=10)
        audio = self._card(inner, "Sound & vibration")
        audio.pack(fill="x", pady=16)
        self._label(audio, f"Sound: {self.settings.get('sound') or 'System bell'}", color=MUTED).pack(side="left", padx=18, pady=16)
        vibration = tk.BooleanVar(value=bool(self.settings.get("vibration", True)))
        tk.Checkbutton(audio, text="Vibration cue", variable=vibration,
                       command=lambda: self._set_preference("vibration", vibration.get()),
                       bg=CARD, fg=TEXT, selectcolor=CARD_ALT, activebackground=CARD,
                       activeforeground=TEXT).pack(side="left", padx=8)
        self.snooze_entry = self._entry(audio, str(self.settings.get("snooze", 10)))
        self.snooze_entry.configure(width=4, justify="center")
        self.snooze_entry.pack(side="left", padx=4)
        self._label(audio, "min snooze", color=MUTED).pack(side="left")
        self._button(audio, "Choose audio", self._choose_sound).pack(side="right", padx=18, pady=10)

    def _entry(self, parent, value):
        entry = tk.Entry(parent, bg=CARD_ALT, fg=TEXT, insertbackground=EMERALD, relief="flat", bd=0, font=self.font_body)
        entry.insert(0, value)
        return entry

    def _time_picker(self, parent, value):
        hour, minute = parse_clock_time(value)
        frame = tk.Frame(parent, bg=CARD)
        frame.pack(side="left", padx=12, pady=10)
        hour_var = tk.StringVar(value=str((hour - 1) % 12 + 1))
        minute_var = tk.StringVar(value=f"{minute:02d}")
        ampm_var = tk.StringVar(value="AM" if hour < 12 else "PM")
        for variable, values, width in (
            (hour_var, [str(number) for number in range(1, 13)], 3),
            (minute_var, [f"{number:02d}" for number in range(60)], 3),
            (ampm_var, ["AM", "PM"], 4),
        ):
            spin = tk.Spinbox(frame, textvariable=variable, values=values, width=width,
                              wrap=True, command=lambda: None, bg=CARD_ALT, fg=TEXT,
                              buttonbackground=EMERALD_DARK, insertbackground=EMERALD,
                              relief="flat", bd=0, justify="center", font=self.font_body)
            spin.pack(side="left", padx=2)
        return hour_var, minute_var, ampm_var

    def _combo(self, parent, values, current):
        variable = tk.StringVar(value=current)
        menu = tk.OptionMenu(parent, variable, *values)
        menu.configure(bg=CARD_ALT, fg=TEXT, activebackground=CARD_ACTIVE, activeforeground=TEXT, relief="flat", bd=0, highlightthickness=0)
        menu.variable = variable
        return menu

    def _save_calc(self):
        try:
            latitude = float(self.setting_entries["latitude"].get())
            longitude = float(self.setting_entries["longitude"].get())
            timezone = self.setting_entries["timezone"].get()
            city = self.setting_entries["city"].get().strip()
            if not city:
                raise ValueError
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError
            ZoneInfo(timezone)
            self.settings.update({"city": city, "latitude": latitude, "longitude": longitude, "timezone": timezone,
                                  "method": self.method.variable.get(), "asr": self.asr.variable.get(),
                                  "high_latitude": self.high_latitude.variable.get(),
                                  "hijri_source": self.hijri_source.variable.get(),
                                  "hijri_language": self.hijri_language.variable.get()})
            adjustments = {}
            for prayer, field in self.adjustment_entries.items():
                value = int(field.get())
                if not -720 <= value <= 720:
                    raise ValueError
                adjustments[prayer] = value
            snooze = int(self.snooze_entry.get())
            if not 1 <= snooze <= 120:
                raise ValueError
            self.settings["adjustments"] = adjustments
            self.settings["snooze"] = snooze
            save_settings(self.settings)
            self._show_page("Dashboard")
        except (ValueError, KeyError):
            messagebox.showerror("Invalid settings", "Check coordinates and use an IANA zone such as Asia/Dhaka.")

    def _sync_now(self):
        if self._data_sync_running or self._hijri_sync_running:
            return
        self._data_sync_running = True
        if getattr(self, "sync_status_label", None):
            self.sync_status_label.configure(text="Connecting...")
        day = datetime.now(ZoneInfo(self.settings["timezone"])).date()
        source = self.settings.get("hijri_source", HIJRI_SOURCES[0])
        threading.Thread(target=self._manual_sync_worker, args=(day, source), daemon=True).start()

    def _sync_status_text(self):
        connection = self.settings.get("internet_sync_status", "Internet: Not checked")
        hijri = self.settings.get("hijri_sync_status", "Hijri: Not synced")
        prayer = self.settings.get("prayer_sync_status", "Prayer: Not synced")
        checked_at = self.settings.get("internet_checked_at", "")
        suffix = f" ({checked_at})" if checked_at else ""
        return f"{connection}{suffix}\n{hijri}\n{prayer}"

    def _manual_sync_worker(self, day, source):
        online = check_internet()
        checked_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        result = sync_hijri_date(day, source)
        prayer_result = None
        try:
            self.settings["internet_sync_status"] = (
                "Internet: Connected" if online else "Internet: Disconnected")
            self.settings["internet_checked_at"] = checked_at
            prayer_result = sync_prayer_schedule(day, self.settings) if online else None
            if result:
                self.settings["hijri_cache"] = result
                self.settings["hijri_sync_status"] = f"Synced: {source}"
            elif not online:
                self.settings["hijri_sync_status"] = "Offline: no internet connection"
            else:
                self.settings["hijri_sync_status"] = f"Online, but {source} has no supported endpoint"
            if prayer_result:
                self.settings["prayer_online_cache"] = prayer_result
                self.settings["prayer_sync_status"] = "Prayer: Online reference"
            else:
                cache_prayer_schedule(day, self.settings)
                self.settings["prayer_sync_status"] = "Prayer: Offline calculated"
            save_settings(self.settings)
        finally:
            self.after(0, lambda: self._finish_manual_sync(day, bool(result), online, bool(prayer_result)))

    def _finish_manual_sync(self, day, synced, online, prayer_synced):
        self._data_sync_running = False
        status = self.settings.get("hijri_sync_status", "Offline Calculated")
        if getattr(self, "sync_status_label", None):
            self.sync_status_label.configure(text=self._sync_status_text())
        self._refresh_hijri(day)
        if not online:
            messagebox.showwarning(
                "No internet connection",
                "The reference service could not be reached. Cached/local calculation remains active.",
            )
        elif not synced and not prayer_synced:
            messagebox.showwarning(
                "Online source unavailable",
                "Internet is available, but the selected Hijri source has no supported endpoint. "
                "Choose Saudi Umm Al-Qura for online Hijri sync.",
            )

    def _choose_sound(self):
        chosen = filedialog.askopenfilename(
            filetypes=[("Audio files", "*.wav *.mp3"), ("WAV audio", "*.wav"), ("MP3 audio", "*.mp3")]
        )
        if chosen:
            if not os.path.isfile(chosen):
                messagebox.showerror("Audio", "The selected audio file no longer exists.")
                return
            self.settings["sound"] = chosen
            save_settings(self.settings)
            self._show_page("Settings")

    def _set_preference(self, key, value):
        self.settings[key] = value
        save_settings(self.settings)

    def _tools(self):
        if self._stopwatch_after_id is None and self.stopwatch_start is not None:
            self._schedule_stopwatch_animation()
        tools = self._tools_scroll_host()

        focus = self._card(tools, "Focus session", accent=True)
        self.focus_card = focus
        focus.pack(fill="x", pady=(0, 10))
        focus_body = tk.Frame(focus, bg=CARD_ACTIVE)
        focus_body.pack(fill="x", padx=18, pady=(0, 8))
        focus_left = tk.Frame(focus_body, bg=CARD_ACTIVE)
        focus_left.pack(side="left", fill="both", expand=True)
        self.study_phase_label = self._label(focus_left, "FOCUS SESSION", self.font_small, GOLD)
        self.study_phase_label.pack(anchor="w", pady=(0, 2))
        self.study_label = self._label(focus_left, "Study 25:00", ("Segoe UI Semibold", 34), EMERALD)
        self.study_label.pack(anchor="w")
        self.study_progress_label = self._label(focus_left, "Progress 0%  ·  Target 25m",
                                                self.font_small, MUTED)
        self.study_progress_label.pack(anchor="w", pady=(1, 0))
        self.study_stats_label = self._label(focus_left, "", self.font_small, TEXT)
        self.study_stats_label.pack(anchor="w", pady=(2, 0))
        self.study_streak_label = self._label(focus_left, "", self.font_small, MUTED)
        self.study_streak_label.pack(anchor="w", pady=(2, 0))
        self.study_totals = self._label(focus_left, "", self.font_small, GOLD)
        self.study_totals.pack(anchor="w", pady=(6, 0))

        self.focus_ring = tk.Canvas(focus_body, width=92, height=92, bg=CARD_ACTIVE, highlightthickness=0)
        self.focus_ring.pack(side="right", padx=(12, 8), pady=(0, 2))
        focus_controls = tk.Frame(focus, bg=CARD_ACTIVE)
        focus_controls.pack(fill="x", padx=18, pady=(0, 10))
        self.study_start_button = self._button(
            focus_controls, "Start Study", lambda: self._start_study_phase("Study"), True)
        self.study_start_button.pack(side="left", padx=(0, 4))
        self._button(focus_controls, "Start Break", lambda: self._start_study_phase("Break")).pack(side="left", padx=4)
        self._button(focus_controls, "Pause", self._study_pause).pack(side="left", padx=4)
        self._button(focus_controls, "Reset", self._study_reset).pack(side="left", padx=4)
        self._button(focus_controls, "Fullscreen", self._toggle_study_fullscreen).pack(side="right", padx=2)
        focus_settings = tk.Frame(focus, bg=CARD_ACTIVE)
        focus_settings.pack(fill="x", padx=18, pady=(0, 10))
        self._label(focus_settings, "Study min", self.font_small, MUTED).pack(side="left")
        self.study_minutes_entry = self._entry(focus_settings, str(self.settings.get("study_minutes", 25)))
        self.study_minutes_entry.configure(width=3, justify="center")
        self.study_minutes_entry.pack(side="left", padx=(5, 12))
        self._label(focus_settings, "Break min", self.font_small, MUTED).pack(side="left")
        self.study_break_entry = self._entry(focus_settings, str(self.settings.get("break_minutes", 5)))
        self.study_break_entry.configure(width=3, justify="center")
        self.study_break_entry.pack(side="left", padx=(5, 8))
        self._label(focus_settings, "Daily goal h", self.font_small, MUTED).pack(side="left", padx=(8, 3))
        self.study_goal_entry = self._entry(
            focus_settings, str(self.settings.get("focus_daily_goal_hours", 8)))
        self.study_goal_entry.configure(width=4, justify="center")
        self.study_goal_entry.pack(side="left", padx=(2, 8))
        self._button(focus_settings, "Save Times", self._save_study_times).pack(side="left", padx=3)
        sound_row = tk.Frame(focus, bg=CARD_ACTIVE)
        sound_row.pack(fill="x", padx=18, pady=(0, 7))
        study_sound_row = tk.Frame(sound_row, bg=CARD_ACTIVE)
        study_sound_row.pack(fill="x", pady=1)
        self._label(study_sound_row, "Study music", self.font_small, MUTED).pack(side="left")
        self.study_sound_label = self._label(study_sound_row,
            os.path.basename(self.settings.get("study_sound", "")) if self.settings.get("study_sound") else "System bell",
            self.font_small, MUTED)
        self.study_sound_label.pack(side="left", padx=(5, 8))
        self._button(study_sound_row, "Choose", lambda: self._choose_tool_sound("study_sound")).pack(side="left", padx=3)
        self._button(study_sound_row, "Test", lambda: self._test_focus_sound("study_sound")).pack(side="left", padx=3)
        self.study_sound_enabled = tk.BooleanVar(value=bool(self.settings.get("study_sound_enabled", True)))
        self.study_sound_state = tk.StringVar()
        self._refresh_focus_sound_state("study_sound_enabled")
        tk.Checkbutton(study_sound_row, textvariable=self.study_sound_state, variable=self.study_sound_enabled,
                       command=lambda: self._set_focus_sound_enabled("study_sound_enabled", self.study_sound_enabled.get()),
                       bg=CARD_ACTIVE, fg=TEXT, selectcolor=CARD_ALT, activebackground=CARD_ACTIVE,
                       activeforeground=TEXT).pack(side="left", padx=10)

        break_sound_row = tk.Frame(sound_row, bg=CARD_ACTIVE)
        break_sound_row.pack(fill="x", pady=1)
        self._label(break_sound_row, "Break music", self.font_small, MUTED).pack(side="left")
        self.break_sound_label = self._label(
            break_sound_row,
            os.path.basename(self.settings.get("break_sound", "")) if self.settings.get("break_sound") else "Off",
            self.font_small, MUTED)
        self.break_sound_label.pack(side="left", padx=(5, 8))
        self._button(break_sound_row, "Choose", lambda: self._choose_tool_sound("break_sound")).pack(side="left", padx=3)
        self._button(break_sound_row, "Test", lambda: self._test_focus_sound("break_sound")).pack(side="left", padx=3)
        self.break_sound_enabled = tk.BooleanVar(value=bool(self.settings.get("break_sound_enabled", True)))
        self.break_sound_state = tk.StringVar()
        self._refresh_focus_sound_state("break_sound_enabled")
        tk.Checkbutton(break_sound_row, textvariable=self.break_sound_state, variable=self.break_sound_enabled,
                       command=lambda: self._set_focus_sound_enabled("break_sound_enabled", self.break_sound_enabled.get()),
                       bg=CARD_ACTIVE, fg=TEXT, selectcolor=CARD_ALT, activebackground=CARD_ACTIVE,
                       activeforeground=TEXT).pack(side="left", padx=10)
        volume_row = tk.Frame(focus, bg=CARD_ACTIVE)
        volume_row.pack(fill="x", padx=18, pady=(0, 9))
        self._label(volume_row, "Study volume", self.font_small, MUTED).pack(side="left")
        self.study_volume = tk.Spinbox(
            volume_row, from_=0, to=100, width=4,
            bg=CARD_ALT, fg=TEXT, buttonbackground=EMERALD_DARK,
            insertbackground=EMERALD, relief="flat", bd=0, justify="center",
            font=self.font_body, command=lambda: self._save_focus_volume("study_sound_volume", self.study_volume))
        self.study_volume.delete(0, "end")
        self.study_volume.insert(0, str(self.settings.get("study_sound_volume", 70)))
        self.study_volume.pack(side="left", padx=(5, 16))
        self._label(volume_row, "Break volume", self.font_small, MUTED).pack(side="left")
        self.break_volume = tk.Spinbox(
            volume_row, from_=0, to=100, width=4,
            bg=CARD_ALT, fg=TEXT, buttonbackground=EMERALD_DARK,
            insertbackground=EMERALD, relief="flat", bd=0, justify="center",
            font=self.font_body, command=lambda: self._save_focus_volume("break_sound_volume", self.break_volume))
        self.break_volume.delete(0, "end")
        self.break_volume.insert(0, str(self.settings.get("break_sound_volume", 70)))
        self.break_volume.pack(side="left", padx=5)
        self._button(volume_row, "Save volume", self._save_focus_volumes).pack(side="left", padx=10)
        self._update_study_display(0)

        grid = tk.Frame(tools, bg=BG)
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure(0, weight=1, uniform="tools")
        grid.grid_columnconfigure(1, weight=1, uniform="tools")
        grid.grid_rowconfigure(0, weight=1, uniform="tools")
        grid.grid_rowconfigure(1, weight=1, uniform="tools")

        stopwatch = self._card(grid, "Stopwatch")
        stopwatch.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self.stopwatch_label = self._label(stopwatch, "00:00.00", self.font_display, EMERALD)
        self.stopwatch_label.pack(pady=(18, 2))
        self.stopwatch_laps_label = self._label(stopwatch, "Laps: 0", self.font_small, MUTED)
        self.stopwatch_laps_label.pack()
        controls = tk.Frame(stopwatch, bg=CARD)
        controls.pack(pady=14)
        self._button(controls, "Start", self._stopwatch_start, True).pack(side="left", padx=3)
        self._button(controls, "Pause", self._stopwatch_pause).pack(side="left", padx=3)
        self._button(controls, "Lap", self._stopwatch_lap).pack(side="left", padx=3)
        self._button(controls, "Reset", self._stopwatch_reset).pack(side="left", padx=3)

        timer = self._card(grid, "Timer")
        timer.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
        self.timer_label = self._label(timer, "00:00:00", self.font_display, GOLD)
        self.timer_label.pack(pady=(18, 2))
        self._label(timer, "COUNTDOWN TIMER", self.font_small, MUTED).pack()
        inputs = tk.Frame(timer, bg=CARD)
        inputs.pack(pady=8)
        self.timer_entries = []
        for value, maximum in (("00", 23), ("05", 59), ("00", 59)):
            field = tk.Spinbox(inputs, from_=0, to=maximum, wrap=True, width=4,
                               format="%02.0f", bg=CARD_ALT, fg=TEXT,
                               buttonbackground=EMERALD_DARK, insertbackground=EMERALD,
                               relief="flat", bd=0, justify="center", font=self.font_body)
            field.delete(0, "end")
            field.insert(0, value)
            field.pack(side="left", padx=3)
            self.timer_entries.append(field)
        presets = tk.Frame(timer, bg=CARD)
        presets.pack()
        for minutes in (1, 5, 10, 25, 45):
            self._button(presets, f"{minutes}m", lambda value=minutes: self._set_timer_preset(value)).pack(side="left", padx=2)
        controls = tk.Frame(timer, bg=CARD)
        controls.pack(pady=10)
        self._button(controls, "Start", self._start_timer, True).pack(side="left", padx=3)
        self._button(controls, "Pause", self._pause_timer).pack(side="left", padx=3)
        self._button(controls, "Reset", self._reset_timer).pack(side="left", padx=3)

        tasbih = self._card(grid, "Tasbih")
        tasbih.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(8, 0))
        self.tasbih_label = self._label(tasbih, str(self.settings.get("tasbih_count", 0)), self.font_display, EMERALD)
        self.tasbih_label.pack(pady=(18, 2))
        self.tasbih_daily_label = self._label(
            tasbih, f"Daily count: {self.settings.get('tasbih_daily', 0)}  |  Double-click +10",
            self.font_small, MUTED)
        self.tasbih_daily_label.pack()
        actions = tk.Frame(tasbih, bg=CARD)
        actions.pack(pady=14)
        self._button(actions, "+", self._increment_tasbih, True).pack(side="left", padx=3)
        self._button(actions, "−", self._decrement_tasbih).pack(side="left", padx=3)
        self._button(actions, "Reset", self._reset_tasbih).pack(side="left", padx=3)
        tasbih.bind("<Double-Button-1>", lambda event: self._increment_tasbih(10))

        notes = self._card(grid, "Quick notes")
        notes.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(8, 0))
        self.notes_text = tk.Text(notes, height=4, bg=CARD_ALT, fg=TEXT, insertbackground=EMERALD,
                                  relief="flat", bd=0, font=("Segoe UI Variable", 12), wrap="word")
        self.notes_text.pack(fill="both", expand=True, padx=16, pady=(12, 6))
        if self.settings.get("quick_notes"):
            self.notes_text.insert("1.0", self.settings["quick_notes"])
        else:
            self.notes_text.insert("1.0", "Capture an idea...")
            self.notes_text.tag_add("placeholder", "1.0", "end")
            self.notes_text.tag_configure("placeholder", foreground=MUTED)
        self.notes_text.bind("<FocusIn>", self._clear_notes_placeholder)
        self.notes_text.bind("<KeyRelease>", self._schedule_note_save)
        note_footer = tk.Frame(notes, bg=CARD)
        note_footer.pack(fill="x", padx=16, pady=(0, 10))
        self.note_saved_label = self._label(note_footer, self._last_saved_text(), self.font_small, MUTED)
        self.note_saved_label.pack(side="left")
        self._button(note_footer, "Save", self._save_note_now, True).pack(side="right")

    def _next_prayer_summary(self):
        now = datetime.now(ZoneInfo(self.settings["timezone"]))
        prayers = calculate_prayers(now.date(), self.settings)
        future = [(value, name) for name, value in prayers.items() if value and value > now]
        if not future:
            return "Tomorrow"
        value, name = min(future)
        return f"{name} · {value.strftime('%I:%M %p').lstrip('0')}"

    @staticmethod
    def _tools_focus(widget):
        if widget:
            widget.focus_set()

    def _increment_tasbih_by(self, amount):
        self.settings["tasbih_count"] = max(0, int(self.settings.get("tasbih_count", 0)) + amount)
        self.settings["tasbih_daily"] = max(0, int(self.settings.get("tasbih_daily", 0)) + amount)
        save_settings(self.settings)
        if self.tasbih_label:
            self.tasbih_label.configure(text=str(self.settings["tasbih_count"]))
        if self.tasbih_daily_label:
            self.tasbih_daily_label.configure(text=f"Daily count: {self.settings['tasbih_daily']}  |  Double-click +10")

    def _increment_tasbih(self, amount=1):
        self._increment_tasbih_by(amount)

    def _decrement_tasbih(self):
        self._increment_tasbih_by(-1)

    def _reset_tasbih(self):
        self.settings["tasbih_count"] = 0
        save_settings(self.settings)
        if self.tasbih_label:
            self.tasbih_label.configure(text="0")

    def _stopwatch_start(self):
        if self.stopwatch_start is None:
            self._stopwatch_toggle()

    def _stopwatch_pause(self):
        if self.stopwatch_start is not None:
            self._stopwatch_toggle()

    def _save_quick_note(self):
        self._save_note_now()

    def _last_saved_text(self):
        value = self.settings.get("quick_notes_saved_at", "")
        return f"Last saved: {value}" if value else "Not saved yet"

    def _schedule_note_save(self, _event=None):
        if getattr(self, "_note_save_after_id", None):
            self.after_cancel(self._note_save_after_id)
        self._note_save_after_id = self.after(350, self._save_note_now)

    def _save_note_now(self):
        if not getattr(self, "notes_text", None):
            return
        note = self.notes_text.get("1.0", "end-1c")
        if note == "Capture an idea...":
            note = ""
        self.settings["quick_notes"] = note
        self.settings["quick_notes_saved_at"] = datetime.now().strftime("%I:%M %p").lstrip("0")
        save_settings(self.settings)
        self._note_save_after_id = None
        if getattr(self, "note_saved_label", None) and self.note_saved_label.winfo_exists():
            self.note_saved_label.configure(text=f"✓ Note saved  ·  {self._last_saved_text()}")
        if getattr(self, "notes_text", None) and self.notes_text.winfo_exists():
            self.after(1400, lambda: self.note_saved_label.configure(text=self._last_saved_text())
                       if self.note_saved_label.winfo_exists() else None)

    def _clear_notes_placeholder(self, _event=None):
        if self.notes_text.get("1.0", "end-1c") == "Capture an idea...":
            self.notes_text.delete("1.0", "end")
            self.notes_text.tag_delete("placeholder")

    def _about(self):
        panel = self._card(self.content, accent=True)
        panel.pack(fill="both", expand=True)
        self._label(panel, "Zishan Islamic Clock", ("Segoe UI Semibold", 28), TEXT).pack(pady=(100, 8))
        self._label(panel, "Designed & Developed by Zishan AI Masters", ("Segoe UI", 14), GOLD).pack()
        self._label(panel, "A privacy-first desktop clock with offline prayer calculations, configurable alarms, and focused time tools.", color=MUTED, wraplength=620).pack(pady=(36, 8))
        self._label(panel, "Prayer times are calculated locally and may differ from an official mosque timetable. Location is stored locally; no ads, analytics, accounts, or tracking are included.", color=MUTED, wraplength=620, justify="center").pack(pady=8)
        self._label(panel, "Windows alarms and timers require the app process to remain open; sleep, termination, and system policy can delay or prevent delivery.", color=MUTED, wraplength=620, justify="center").pack(pady=8)

    def _quran(self):
        panel = self._card(self.content, accent=True)
        panel.pack(fill="both", expand=True)
        self._label(panel, "Al-Quran", ("Segoe UI Semibold", 28), TEXT).pack(pady=(150, 8))
        self._label(panel, "Coming Soon", ("Segoe UI", 16), GOLD).pack()

    def _toggle_fullscreen(self):
        if getattr(self, "clock_overlay", None) and self.clock_overlay.winfo_exists():
            self._close_clock_overlay()
            return
        overlay = tk.Toplevel(self)
        self.clock_overlay = overlay
        overlay.configure(bg=BG)
        overlay.attributes("-fullscreen", True)
        overlay.bind("<Escape>", lambda event: self._close_clock_overlay())
        overlay.protocol("WM_DELETE_WINDOW", self._close_clock_overlay)
        top = tk.Frame(overlay, bg=BG)
        top.pack(fill="x", padx=32, pady=24)
        tk.Label(top, text="ZISHAN ISLAMIC CLOCK", bg=BG, fg=MUTED,
                 font=("Segoe UI Semibold", 12)).pack(side="left")
        tk.Button(top, text="×", command=self._close_clock_overlay, bg=BG, fg=TEXT,
                  activebackground=CARD_ACTIVE, activeforeground=TEXT, relief="flat",
                  bd=0, font=("Segoe UI", 22), cursor="hand2").pack(side="right")
        body = tk.Frame(overlay, bg=BG)
        body.pack(expand=True)
        self.overlay_digital = tk.Label(body, text="", bg=BG, fg=EMERALD,
                                        font=("Segoe UI Semibold", 86))
        self.overlay_digital.pack(pady=(20, 4))
        self.overlay_date = tk.Label(body, text="", bg=BG, fg=MUTED,
                                     font=("Segoe UI", 18))
        self.overlay_date.pack()
        self.overlay_analog = tk.Canvas(body, width=420, height=420, bg=BG, highlightthickness=0)
        self.overlay_analog.pack(pady=24)
        self._update_clock_overlay()

    def _close_clock_overlay(self):
        overlay = getattr(self, "clock_overlay", None)
        if overlay and overlay.winfo_exists():
            overlay.destroy()
        self.clock_overlay = None

    def _update_clock_overlay(self):
        overlay = getattr(self, "clock_overlay", None)
        if not overlay or not overlay.winfo_exists():
            return
        now = datetime.now(ZoneInfo(self.settings["timezone"]))
        self.overlay_digital.configure(text=now.strftime("%I:%M:%S %p").lstrip("0"))
        self.overlay_date.configure(text=now.strftime("%A, %d %B %Y"))
        self._draw_analog(now, self.overlay_analog, 210)
        overlay.after(500, self._update_clock_overlay)

    def _edit_study_settings(self):
        dialog = tk.Toplevel(self)
        dialog.title("Study break settings")
        dialog.configure(bg=CARD)
        dialog.transient(self)
        dialog.grab_set()
        fields = {}
        for label, key, default in (
            ("Study minutes", "study_minutes", self.settings.get("study_minutes", 25)),
            ("Break minutes", "break_minutes", self.settings.get("break_minutes", 5)),
        ):
            row = tk.Frame(dialog, bg=CARD)
            row.pack(fill="x", padx=24, pady=8)
            self._label(row, label, color=MUTED, width=18, anchor="w").pack(side="left")
            field = self._entry(row, str(default))
            field.configure(width=6, justify="center")
            field.pack(side="left")
            fields[key] = field

        def save():
            try:
                study = int(fields["study_minutes"].get())
                pause = int(fields["break_minutes"].get())
                if not 1 <= study <= 1440 or not 1 <= pause <= 180:
                    raise ValueError
                self.settings.update({"study_minutes": study, "break_minutes": pause})
                save_settings(self.settings)
                self._study_reset()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Study break", "Study must be 1–1440 minutes and break 1–180 minutes.")

        self._button(dialog, "Save", save, True).pack(pady=(8, 20))

    def _save_study_times(self):
        try:
            study = int(self.study_minutes_entry.get())
            pause = int(self.study_break_entry.get())
            goal = float(self.study_goal_entry.get())
            if not 1 <= study <= 1440 or not 1 <= pause <= 180 or not 1 <= goal <= 24:
                raise ValueError
            self.settings.update({
                "study_minutes": study,
                "break_minutes": pause,
                "focus_daily_goal_hours": goal,
            })
            save_settings(self.settings)
            self._study_reset()
            self._update_study_display(0)
        except ValueError:
            messagebox.showerror(
                "Focus settings",
                "Study: 1–1440 minutes, break: 1–180 minutes, daily goal: 1–24 hours.",
            )

    def _choose_tool_sound(self, key):
        chosen = filedialog.askopenfilename(
            filetypes=[("Audio files", "*.wav *.mp3"), ("WAV audio", "*.wav"), ("MP3 audio", "*.mp3")]
        )
        if chosen:
            if not os.path.isfile(chosen):
                messagebox.showerror("Focus sound", "The selected audio file no longer exists.")
                return
            self.settings[key] = chosen
            enabled_key = f"{key}_enabled"
            self.settings[enabled_key] = True
            sound_var = getattr(self, f"{key}_enabled", None)
            if sound_var is not None:
                sound_var.set(True)
            save_settings(self.settings)
            if key == "study_sound" and getattr(self, "study_sound_label", None):
                self.study_sound_label.configure(text=os.path.basename(chosen))
            if key == "break_sound" and getattr(self, "break_sound_label", None):
                self.break_sound_label.configure(text=os.path.basename(chosen))

    def _set_focus_sound_enabled(self, key, enabled):
        self.settings[key] = bool(enabled)
        self._refresh_focus_sound_state(key)
        save_settings(self.settings)
        current_key = "study_sound_enabled" if self.study_phase == "Study" else "break_sound_enabled"
        if not enabled and key == current_key:
            stop_focus_sound()

    def _refresh_focus_sound_state(self, key):
        state = "Music ON" if self.settings.get(key, True) else "Music OFF"
        variable = getattr(self, f"{key.replace('_enabled', '')}_sound_state", None)
        if variable is not None:
            variable.set(state)

    def _test_focus_sound(self, key):
        if not self.settings.get(key):
            messagebox.showwarning("Focus music", "Choose a WAV or MP3 file first.")
            return
        stop_focus_sound()
        if not play_focus_sound(self.settings[key], self.settings.get(f"{key}_volume", 70)):
            messagebox.showerror(
                "Focus music",
                "This file could not be played. Use a valid local WAV or MP3 file.",
            )

    def _save_focus_volume(self, key, field):
        try:
            value = int(field.get())
            if not 0 <= value <= 100:
                raise ValueError
            self.settings[key] = value
            save_settings(self.settings)
        except ValueError:
            messagebox.showerror("Focus sound", "Volume must be between 0 and 100.")

    def _save_focus_volumes(self):
        self._save_focus_volume("study_sound_volume", self.study_volume)
        self._save_focus_volume("break_sound_volume", self.break_volume)

    def _focus_week_key(self, value=None):
        value = value or datetime.now(ZoneInfo(self.settings["timezone"])).date()
        return f"{value.isocalendar().year}-W{value.isocalendar().week:02d}"

    def _load_focus_stats(self):
        stats = self.settings.setdefault("focus_stats", {})
        today = datetime.now(ZoneInfo(self.settings["timezone"])).date().isoformat()
        week = self._focus_week_key()
        self.study_today_seconds = float(stats.get("today", {}).get(today, 0))
        self.study_week_seconds = float(stats.get("week", {}).get(week, 0))
        self.study_all_seconds = float(stats.get("all_seconds", 0))
        self.study_sessions_completed = int(stats.get("sessions", 0))

    def _record_study_elapsed(self):
        if self.study_accounted_at is None or self.study_phase != "Study":
            return
        elapsed = max(0.0, time.monotonic() - self.study_accounted_at)
        if elapsed <= 0:
            return
        now = datetime.now(ZoneInfo(self.settings["timezone"]))
        today = now.date().isoformat()
        week = self._focus_week_key(now.date())
        stats = self.settings.setdefault("focus_stats", {})
        stats.setdefault("today", {})[today] = float(stats.setdefault("today", {}).get(today, 0)) + elapsed
        stats.setdefault("week", {})[week] = float(stats.setdefault("week", {}).get(week, 0)) + elapsed
        stats["all_seconds"] = float(stats.get("all_seconds", 0)) + elapsed
        self.study_today_seconds = stats["today"][today]
        self.study_week_seconds = stats["week"][week]
        self.study_all_seconds = stats["all_seconds"]
        self.study_accounted_at = time.monotonic()
        save_settings(self.settings)

    def _play_current_focus_sound(self):
        key = "study_sound" if self.study_phase == "Study" else "break_sound"
        enabled_key = f"{key}_enabled"
        if not self.settings.get(enabled_key, True):
            return
        path = self.settings.get(key, "")
        if path and not play_focus_sound(path, self.settings.get(f"{key}_volume", 70)):
            messagebox.showerror(
                "Focus sound",
                "This audio file could not be played. Select a WAV or MP3 file, then try again.",
            )

    def _study_toggle(self):
        if self.study_running:
            self._study_pause()
        else:
            self._start_study_phase(self.study_phase)

    def _start_study_phase(self, phase):
        stop_focus_sound()
        self._record_study_elapsed()
        was_paused_same_phase = (
            not self.study_running
            and self.study_phase == phase
            and float(self.settings.get("study_phase_remaining", 0)) > 0
        )
        self.study_phase = phase
        if not was_paused_same_phase:
            duration = self.settings.get("study_minutes", 25) if phase == "Study" else self.settings.get("break_minutes", 5)
            self.settings["study_phase_remaining"] = duration * 60
        self.study_running = True
        self.study_accounted_at = time.monotonic() if phase == "Study" else None
        if getattr(self, "focus_card", None):
            self.focus_card.configure(bg=CARD_HOVER, highlightbackground=EMERALD)
        self.study_deadline = time.monotonic() + self.settings["study_phase_remaining"]
        self._play_current_focus_sound()
        self._study_tick()

    def _study_pause(self):
        if not self.study_running or self.study_deadline is None:
            return
        self._record_study_elapsed()
        self.settings["study_phase_remaining"] = max(0, self.study_deadline - time.monotonic())
        self.study_running = False
        self.study_deadline = None
        self.study_accounted_at = None
        stop_focus_sound()
        if getattr(self, "focus_card", None):
            self.focus_card.configure(bg=CARD, highlightbackground=LINE)
        if getattr(self, "study_start_button", None):
            self.study_start_button.configure(text="Resume Study" if self.study_phase == "Study" else "Resume Break")
        if self._study_after_id is not None:
            self.after_cancel(self._study_after_id)
            self._study_after_id = None

    def _study_skip(self):
        self._study_pause()
        self.study_phase = "Break" if self.study_phase == "Study" else "Study"
        self.settings["study_phase_remaining"] = 0
        self._update_study_display(0)

    def _study_reset(self):
        self._record_study_elapsed()
        stop_focus_sound()
        self.study_running = False
        self.study_deadline = None
        self.settings["study_phase_remaining"] = 0
        self.study_phase = "Study"
        self.study_accounted_at = None
        self.study_streak = 0
        if getattr(self, "study_start_button", None):
            self.study_start_button.configure(text="Start Study")
        if self._study_after_id is not None:
            self.after_cancel(self._study_after_id)
            self._study_after_id = None
        self._update_study_display(0)

    def _study_tick(self):
        if not self.study_running or self.study_deadline is None:
            return
        remaining = max(0, self.study_deadline - time.monotonic())
        self._record_study_elapsed()
        self.settings["study_phase_remaining"] = remaining
        self._update_study_display(remaining)
        if remaining <= 0:
            stop_focus_sound()
            if self.study_phase == "Study":
                self.study_streak += 1
                self.study_sessions_completed += 1
                self.settings.setdefault("focus_stats", {})["sessions"] = self.study_sessions_completed
                save_settings(self.settings)
            self.study_phase = "Break" if self.study_phase == "Study" else "Study"
            self.settings["study_phase_remaining"] = 0
            self.study_running = False
            self.study_deadline = None
            self.study_accounted_at = None
            self._update_study_display(0)
            self._start_study_phase(self.study_phase)
            return
        self._study_after_id = self.after(250, self._study_tick)

    def _toggle_study_fullscreen(self):
        overlay = getattr(self, "study_overlay", None)
        if overlay and overlay.winfo_exists():
            self._close_study_fullscreen()
            return
        overlay = tk.Toplevel(self)
        self.study_overlay = overlay
        overlay.configure(bg=BG)
        overlay.attributes("-fullscreen", True)
        overlay.bind("<Escape>", lambda event: self._close_study_fullscreen())
        overlay.protocol("WM_DELETE_WINDOW", self._close_study_fullscreen)
        tk.Button(overlay, text="×", command=self._close_study_fullscreen, bg=BG, fg=TEXT,
                  activebackground=CARD_ACTIVE, activeforeground=TEXT, relief="flat",
                  bd=0, font=("Segoe UI", 22), cursor="hand2").pack(anchor="ne", padx=28, pady=20)
        self.study_overlay_title = tk.Label(overlay, text="STUDY FOCUS", bg=BG, fg=GOLD,
                                            font=("Segoe UI Semibold", 18))
        self.study_overlay_title.pack(pady=(90, 12))
        self.study_overlay_label = tk.Label(overlay, text="", bg=BG, fg=EMERALD,
                                            font=("Segoe UI Semibold", 110))
        self.study_overlay_label.pack(expand=True)
        self.study_cat_canvas = tk.Canvas(
            overlay, width=420, height=126, bg=BG, highlightthickness=0, bd=0)
        self.study_cat_canvas.pack(side="bottom", pady=(0, 34))
        self.study_cat_frame = 0
        self._update_study_fullscreen()

    def _close_study_fullscreen(self):
        overlay = getattr(self, "study_overlay", None)
        if overlay and overlay.winfo_exists():
            overlay.destroy()
        self.study_overlay = None
        self.study_cat_canvas = None

    def _update_study_fullscreen(self):
        overlay = getattr(self, "study_overlay", None)
        if not overlay or not overlay.winfo_exists():
            return
        remaining = self.settings.get("study_phase_remaining", 0)
        if self.study_running and self.study_deadline is not None:
            remaining = max(0, self.study_deadline - time.monotonic())
        seconds = int(max(0, remaining))
        self.study_overlay_title.configure(text=f"{self.study_phase.upper()}  ·  STREAK {self.study_streak}")
        self.study_overlay_label.configure(text=f"{seconds // 60:02d}:{seconds % 60:02d}")
        self._draw_focus_cat()
        overlay.after(250, self._update_study_fullscreen)

    def _draw_focus_cat(self):
        canvas = getattr(self, "study_cat_canvas", None)
        if not canvas or not canvas.winfo_exists():
            return
        canvas.delete("all")
        self.study_cat_frame = (getattr(self, "study_cat_frame", 0) + 1) % 12
        phase = self.study_phase
        accent = EMERALD if phase == "Study" else GOLD
        canvas.create_line(20, 108, 400, 108, fill=LINE, width=2)
        if phase == "Study":
            x = 70 + self.study_cat_frame * 24
            canvas.create_text(210, 18, text="quiet focus companion", fill=MUTED,
                               font=("Segoe UI Variable", 9))
            canvas.create_oval(x - 34, 52, x + 34, 104, fill=accent, outline="")
            canvas.create_oval(x - 22, 30, x + 25, 76, fill=accent, outline="")
            canvas.create_polygon(x - 20, 38, x - 18, 16, x - 3, 32, fill=accent, outline="")
            canvas.create_polygon(x + 5, 32, x + 22, 14, x + 23, 42, fill=accent, outline="")
            canvas.create_oval(x - 10, 48, x - 5, 54, fill=BG, outline="")
            canvas.create_oval(x + 10, 48, x + 15, 54, fill=BG, outline="")
            canvas.create_line(x + 30, 78, x + 52, 62, fill=accent, width=5, smooth=True)
            canvas.create_line(x - 18, 96, x - 22, 108, fill=accent, width=5)
            canvas.create_line(x + 16, 96, x + 20, 108, fill=accent, width=5)
        else:
            x = 210
            canvas.create_text(210, 18, text="break time · snack break", fill=MUTED,
                               font=("Segoe UI Variable", 9))
            canvas.create_oval(x - 42, 58, x + 42, 105, fill=accent, outline="")
            canvas.create_oval(x - 25, 35, x + 27, 82, fill=accent, outline="")
            canvas.create_polygon(x - 22, 42, x - 20, 20, x - 3, 37, fill=accent, outline="")
            canvas.create_polygon(x + 3, 37, x + 22, 19, x + 24, 46, fill=accent, outline="")
            canvas.create_oval(x - 12, 51, x - 7, 57, fill=BG, outline="")
            canvas.create_oval(x + 10, 51, x + 15, 57, fill=BG, outline="")
            canvas.create_oval(x + 48, 86, x + 68, 101, fill=GOLD, outline="")
            canvas.create_line(x + 20, 79, x + 48, 91, fill=accent, width=5)
            canvas.create_line(x - 19, 96, x - 25, 108, fill=accent, width=5)
            canvas.create_line(x + 18, 96, x + 25, 108, fill=accent, width=5)

    def _update_study_display(self, remaining):
        if not getattr(self, "study_label", None):
            return
        if remaining <= 0 and not self.study_running:
            remaining = (self.settings.get("study_minutes", 25) if self.study_phase == "Study"
                         else self.settings.get("break_minutes", 5)) * 60
        seconds = int(max(0, remaining))
        self.study_label.configure(text=f"{self.study_phase} {seconds // 60:02d}:{seconds % 60:02d}")
        self.study_phase_label.configure(text="Focus session" if self.study_phase == "Study" else "Rest session")
        if getattr(self, "study_start_button", None):
            if self.study_running:
                self.study_start_button.configure(text="Running")
            elif self.settings.get("study_phase_remaining", 0) > 0:
                self.study_start_button.configure(
                    text="Resume Study" if self.study_phase == "Study" else "Resume Break")
            else:
                self.study_start_button.configure(text="Start Study")
        if getattr(self, "study_streak_label", None):
            self.study_streak_label.configure(text=f"Focus streak: {self.study_streak} days")
        if getattr(self, "study_stats_label", None):
            self.study_stats_label.configure(
                text=f"Today  {self._format_focus_time(self.study_today_seconds)}  ·  "
                     f"Week  {self._format_focus_time(self.study_week_seconds)}")
        if getattr(self, "focus_ring", None):
            self.focus_ring.delete("all")
            session_duration = (self.settings.get("study_minutes", 25) if self.study_phase == "Study"
                                else self.settings.get("break_minutes", 5)) * 60
            session_progress = min(1, max(0, 1 - seconds / session_duration))
            goal_seconds = float(self.settings.get("focus_daily_goal_hours", 8)) * 3600
            daily_progress = min(1, max(0, self.study_today_seconds / goal_seconds))
            if getattr(self, "study_progress_label", None):
                target = self._format_focus_time(session_duration)
                self.study_progress_label.configure(
                    text=f"Session {int(session_progress * 100)}%  ·  Daily goal "
                         f"{int(daily_progress * 100)}% ({self.settings.get('focus_daily_goal_hours', 8):g}h)")
            self.focus_ring.create_oval(8, 8, 84, 84, outline=LINE, width=8)
            self.focus_ring.create_arc(8, 8, 84, 84, start=90, extent=-360 * daily_progress,
                                       outline=EMERALD if self.study_phase == "Study" else GOLD,
                                       width=8, style="arc")
            self.focus_ring.create_text(46, 46, text=f"{int(daily_progress * 100)}%",
                                        fill=TEXT, font=("Segoe UI Semibold", 10))
        if getattr(self, "study_totals", None):
            self.study_totals.configure(
                text=f"All time  {self._format_focus_time(self.study_all_seconds)}  ·  "
                     f"Sessions {self.study_sessions_completed}")

    @staticmethod
    def _format_focus_time(seconds):
        seconds = int(max(0, seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes = remainder // 60
        return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"

    def _tick(self):
        try:
            now = datetime.now(ZoneInfo(self.settings["timezone"]))
        except (KeyError, ValueError):
            now = datetime.now()
        self.header_meta.configure(text=now.strftime("%A  ·  %d %B %Y"))
        if self.page == "Dashboard":
            self._dashboard_update(now)
        if self.page == "Tools" and hasattr(self, "stopwatch_label"):
            self._update_stopwatch_display()
        if self.page == "Tools" and self.study_running:
            self._update_study_display(max(0, self.study_deadline - time.monotonic()))
        self.after(1000, self._tick)

    def _draw_analog(self, now, canvas=None, radius=78):
        canvas = canvas or self.analog
        canvas.delete("all")
        cx = canvas.winfo_width() // 2 or (radius + 32)
        cy = canvas.winfo_height() // 2 or (radius + 27)
        canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline=EMERALD_DARK, width=3)
        for number in range(1, 13):
            angle = number / 12 * 2 * math.pi - math.pi / 2
            outer = radius - 5
            tick_inner = radius - (14 if number % 3 == 0 else 9)
            canvas.create_line(cx + math.cos(angle) * tick_inner, cy + math.sin(angle) * tick_inner,
                               cx + math.cos(angle) * outer, cy + math.sin(angle) * outer,
                               fill=GOLD if number % 3 == 0 else MUTED, width=2)
            text_radius = radius - 25
            canvas.create_text(cx + math.cos(angle) * text_radius, cy + math.sin(angle) * text_radius,
                               text=str(number), fill=TEXT, font=("Segoe UI Semibold", 12 if radius > 100 else 9))
        for value, divisor, length, width, color in ((now.hour % 12 + now.minute / 60, 12, 38, 6, TEXT),
                                                       (now.minute + now.second / 60, 60, 57, 4, TEXT),
                                                       (now.second, 60, 67, 2, EMERALD)):
            angle = value / divisor * 2 * math.pi - math.pi / 2
            canvas.create_line(cx, cy, cx + math.cos(angle) * length, cy + math.sin(angle) * length, fill=color, width=width)
        canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill=GOLD, outline="")

    def _stopwatch_toggle(self):
        if self.stopwatch_start is None:
            self.stopwatch_start = time.monotonic() - self.stopwatch_elapsed
            self._schedule_stopwatch_animation()
        else:
            self.stopwatch_elapsed = time.monotonic() - self.stopwatch_start
            self.stopwatch_start = None
            self._cancel_stopwatch_animation()
            self._update_stopwatch_display()

    def _stopwatch_reset(self):
        self.stopwatch_start = None
        self.stopwatch_elapsed = 0
        self._cancel_stopwatch_animation()
        self._update_stopwatch_display()
        self.stopwatch_laps = []
        if hasattr(self, "stopwatch_laps_label"):
            self.stopwatch_laps_label.configure(text="Laps: 0")

    def _schedule_stopwatch_animation(self):
        self._cancel_stopwatch_animation()
        self._stopwatch_after_id = self.after(20, self._stopwatch_animation)

    def _cancel_stopwatch_animation(self):
        if self._stopwatch_after_id is not None:
            self.after_cancel(self._stopwatch_after_id)
            self._stopwatch_after_id = None

    def _stopwatch_animation(self):
        self._stopwatch_after_id = None
        self._update_stopwatch_display()
        if self.stopwatch_start is not None:
            self._schedule_stopwatch_animation()

    def _update_stopwatch_display(self):
        if not getattr(self, "stopwatch_label", None):
            return
        elapsed = self.stopwatch_elapsed if self.stopwatch_start is None else time.monotonic() - self.stopwatch_start
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        hundredths = int((elapsed - int(elapsed)) * 100)
        try:
            self.stopwatch_label.configure(text=f"{minutes:02d}:{seconds:02d}.{hundredths:02d}")
        except tk.TclError:
            self.stopwatch_label = None

    def _stopwatch_lap(self):
        elapsed = self.stopwatch_elapsed if self.stopwatch_start is None else time.monotonic() - self.stopwatch_start
        if self.stopwatch_start is None:
            return
        self.stopwatch_laps.append(elapsed)
        if hasattr(self, "stopwatch_laps_label"):
            self.stopwatch_laps_label.configure(
                text=f"Laps: {len(self.stopwatch_laps)}  ·  " +
                     "\n".join(f"Lap {index}: {value // 60:02.0f}:{value % 60:05.2f}"
                               for index, value in enumerate(self.stopwatch_laps, 1))
            )

    def _start_timer(self):
        if not self.timer_running and self.timer_remaining <= 0:
            try:
                hours, minutes, seconds = (int(field.get()) for field in self.timer_entries)
                if hours < 0 or minutes not in range(60) or seconds not in range(60):
                    raise ValueError
                self.timer_remaining = hours * 3600 + minutes * 60 + seconds
                if self.timer_remaining <= 0:
                    raise ValueError
            except (ValueError, AttributeError):
                messagebox.showerror("Timer", "Enter hours, minutes, and seconds (00-59 for minutes and seconds).")
                return
        self.timer_running = True
        self.timer_deadline = time.monotonic() + self.timer_remaining
        self._timer_tick()

    def _set_timer_preset(self, minutes):
        if self.timer_running:
            return
        self.timer_entries[0].delete(0, "end")
        self.timer_entries[0].insert(0, "00")
        self.timer_entries[1].delete(0, "end")
        self.timer_entries[1].insert(0, f"{minutes:02d}")
        self.timer_entries[2].delete(0, "end")
        self.timer_entries[2].insert(0, "00")

    def _pause_timer(self):
        if self.timer_running and self.timer_deadline is not None:
            self.timer_remaining = max(0, self.timer_deadline - time.monotonic())
            self.timer_running = False
            self.timer_deadline = None

    def _reset_timer(self):
        self.timer_running = False
        self.timer_deadline = None
        self.timer_remaining = 0
        if hasattr(self, "timer_label"):
            self.timer_label.configure(text="00:00:00")

    def _timer_tick(self):
        if not self.timer_running or self.timer_deadline is None:
            return
        remaining = max(0, self.timer_deadline - time.monotonic())
        whole = int(remaining)
        self.timer_remaining = remaining
        self.timer_label.configure(text=f"{whole // 3600:02d}:{(whole % 3600) // 60:02d}:{whole % 60:02d}")
        if remaining:
            self.after(100, self._timer_tick)
        else:
            self.timer_running = False
            self.timer_deadline = None
            self._ring("Timer finished")

    def _start_alarm_monitor(self):
        self._alarm_last_keys = set()
        self._alarm_monitor()

    def _alarm_monitor(self):
        zone = ZoneInfo(self.settings["timezone"])
        now = datetime.now(zone).replace(second=0, microsecond=0)
        key_base = now.isoformat()
        for item in scheduled_prayer_events(now.date(), self.settings):
            if item["time"].replace(second=0, microsecond=0) == now:
                key = f"prayer:{item['id']}"
                if key not in self._alarm_last_keys:
                    self._alarm_last_keys.add(key)
                    self._ring(f"{item['prayer']} {item['event'].title()}")
        for index, alarm in enumerate(self.settings.get("general_alarms", [])):
            occurrence = next_general_alarm(alarm, now - timedelta(minutes=1))
            if occurrence and occurrence.replace(second=0, microsecond=0) == now:
                key = f"general:{index}:{key_base}"
                if key not in self._alarm_last_keys:
                    self._alarm_last_keys.add(key)
                    self._ring(alarm.get("label", "General alarm"))
        if len(self._alarm_last_keys) > 200:
            self._alarm_last_keys = {key for key in self._alarm_last_keys if key.endswith(key_base)}
        self._alarm_after_id = self.after(5000, self._alarm_monitor)

    def _ring(self, title):
        sound = self.settings.get("sound", "")
        if sound.lower().endswith((".wav", ".mp3")) and os.path.isfile(sound):
            play_alarm_sound(sound)
        else:
            self.bell()
        dialog = tk.Toplevel(self)
        dialog.title("Zishan Islamic Clock")
        dialog.configure(bg=CARD_ACTIVE)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._label(dialog, title, ("Segoe UI Semibold", 20), TEXT).pack(padx=34, pady=(28, 8))
        self._label(dialog, "Alarm is ringing", color=MUTED).pack(padx=34, pady=(0, 20))
        controls = tk.Frame(dialog, bg=CARD_ACTIVE)
        controls.pack(pady=(0, 26))

        def finish():
            stop_alarm_sound()
            dialog.grab_release()
            dialog.destroy()

        def snooze():
            finish()
            self.after(max(1, int(self.settings.get("snooze", 10))) * 60 * 1000, lambda: self._ring(f"{title} (snoozed)"))

        self._button(controls, "Snooze", snooze, True).pack(side="left", padx=5)
        self._button(controls, "Dismiss", finish).pack(side="left", padx=5)
