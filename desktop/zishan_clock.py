import json
import math
import os
import threading
import time
import urllib.parse
import urllib.request
import tkinter as tk
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from zoneinfo import ZoneInfo

try:
    import winsound
except ImportError:  # Non-Windows development environments
    winsound = None


def play_alarm_sound(path: str) -> None:
    """Play a selected WAV or MP3 using the Windows-native available player."""
    if not path:
        return
    extension = Path(path).suffix.lower()
    if extension == ".wav" and winsound:
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    elif extension == ".mp3" and os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]


def stop_alarm_sound() -> None:
    if winsound:
        winsound.PlaySound(None, 0)


def play_focus_sound(path: str, volume: int = 70) -> bool:
    """Loop a selected WAV or MP3 and return whether playback started."""
    if not path or not os.path.isfile(path):
        return False
    volume = max(0, min(100, int(volume)))
    if os.name == "nt":
        try:
            import ctypes
            winmm = ctypes.windll.winmm
            winmm.mciSendStringW(f"close {_FOCUS_SOUND_ALIAS}", None, 0, None)
            device = "mpegvideo" if path.lower().endswith(".mp3") else "waveaudio"
            if winmm.mciSendStringW(
                f'open "{path}" type {device} alias {_FOCUS_SOUND_ALIAS}', None, 0, None
            ) == 0:
                winmm.mciSendStringW(
                    f"setaudio {_FOCUS_SOUND_ALIAS} volume to {volume * 10}", None, 0, None
                )
                if winmm.mciSendStringW(
                    f"play {_FOCUS_SOUND_ALIAS} repeat", None, 0, None
                ) == 0:
                    return True
                winmm.mciSendStringW(f"close {_FOCUS_SOUND_ALIAS}", None, 0, None)
        except (AttributeError, OSError):
            pass
    if path.lower().endswith(".wav") and winsound:
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        return True
    return False


def stop_focus_sound() -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.winmm.mciSendStringW(f"close {_FOCUS_SOUND_ALIAS}", None, 0, None)
        except (AttributeError, OSError):
            pass
    stop_alarm_sound()


METHODS = {
    "Muslim World League": (18.0, 17.0),
    "Karachi": (18.0, 18.0),
    "Egyptian": (19.5, 17.5),
    "North America": (15.0, 15.0),
    "Singapore": (20.0, 18.0),
}

_FOCUS_SOUND_ALIAS = "ZishanFocusSound"
PRAYERS = ("Fajr", "Dhuhr", "Asr", "Maghrib", "Isha")
DAYLIGHT_EVENTS = ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha")
EVENTS = ("azan", "reminder")
DEFAULT_LOCATION = {
    "city": "Chattogram, Bangladesh",
    "latitude": 22.3569,
    "longitude": 91.7832,
    "timezone": "Asia/Dhaka",
}
DEFAULTS = {
    **DEFAULT_LOCATION,
    "method": "Muslim World League",
    "asr": "Hanafi",
    "high_latitude": "Middle of the night",
    "adjustments": {name: 0 for name in PRAYERS},
    "prayer_alarms": {},
    "prayer_events": {},
    "general_alarms": [],
    "sound": "",
    "study_sound": "",
    "break_sound": "",
    "study_sound_enabled": True,
    "break_sound_enabled": True,
    "study_sound_volume": 70,
    "break_sound_volume": 70,
    "study_minutes": 25,
    "break_minutes": 5,
    "focus_daily_goal_hours": 8,
    "focus_stats": {},
    "tasbih_count": 0,
    "tasbih_daily": 0,
    "tasbih_best_day": 0,
    "quick_notes": "",
    "quick_notes_saved_at": "",
    "vibration": True,
    "snooze": 10,
    "hijri_source": "Bangladesh Official",
    "hijri_language": "English",
    "hijri_cache": {},
    "prayer_cache": {},
}

HIJRI_SOURCES = (
    "Bangladesh Official",
    "Saudi Umm Al-Qura",
    "Global Moon Sighting",
)
HIJRI_LANGUAGES = ("English", "Arabic", "Both")
HIJRI_MONTH_NAMES = (
    "Muharram", "Safar", "Rabi al-Awwal", "Rabi al-Thani",
    "Jumada al-Ula", "Jumada al-Thaniyah", "Rajab", "Sha'ban",
    "Ramadan", "Shawwal", "Dhu al-Qadah", "Dhu al-Hijjah",
)
HIJRI_ARABIC_MONTH_NAMES = (
    "محرم", "صفر", "ربيع الأول", "ربيع الثاني", "جمادى الأولى", "جمادى الثانية",
    "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة",
)


def offline_hijri(gregorian: date) -> dict:
    """Return a deterministic offline lunar-calendar approximation.

    The civil anchor is the Bangladesh-facing reference used by the desktop
    product: 2026-10-31 = 10 Rabi al-Thani 1448 AH. Synced data replaces it
    when the selected online source succeeds.
    """
    anchor = date(2026, 10, 31)
    year, month, day = 1448, 4, 10
    delta = (gregorian - anchor).days
    month_lengths = (30, 29) * 6
    while delta > 0:
        day += 1
        delta -= 1
        if day > month_lengths[(month - 1) % 12]:
            day = 1
            month += 1
            if month == 13:
                month, year = 1, year + 1
    while delta < 0:
        day -= 1
        delta += 1
        if day < 1:
            month -= 1
            if month == 0:
                month, year = 12, year - 1
            day = month_lengths[(month - 1) % 12]
    return {"day": day, "month": month, "year": year,
            "month_name": HIJRI_MONTH_NAMES[month - 1],
            "arabic_month": HIJRI_ARABIC_MONTH_NAMES[month - 1],
            "source": "Calculated Offline"}


def sync_hijri_date(gregorian: date, source: str, timeout: float = 4.0) -> dict | None:
    """Fetch an online Hijri reference without making network access mandatory.

    Aladhan's method 4 is the Umm al-Qura reference. If a selected regional
    source has no endpoint, the same online reference is returned as an
    explicitly labelled fallback rather than being misrepresented as official.
    """
    query = urllib.parse.urlencode({"date": gregorian.strftime("%d-%m-%Y"), "method": 4})
    request = urllib.request.Request(
        f"https://api.aladhan.com/v1/gToH?{query}",
        headers={"User-Agent": "ZishanIslamicClock/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        hijri = payload["data"]["hijri"]
        return {
            "day": int(hijri["day"]),
            "month": int(hijri["month"]["number"]),
            "year": int(hijri["year"]),
            "month_name": HIJRI_MONTH_NAMES[int(hijri["month"]["number"]) - 1],
            "arabic_month": HIJRI_ARABIC_MONTH_NAMES[int(hijri["month"]["number"]) - 1],
            "source": source if source == "Saudi Umm Al-Qura" else "Online reference fallback",
            "requested_source": source,
            "synced_date": gregorian.isoformat(),
            "synced_at": datetime.now().isoformat(timespec="seconds"),
        }
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def check_internet(timeout: float = 4.0) -> bool:
    """Check the same reference service used for optional date/prayer sync."""
    today = datetime.now().strftime("%d-%m-%Y")
    request = urllib.request.Request(
        f"https://api.aladhan.com/v1/gToH?date={today}&method=4",
        headers={"User-Agent": "ZishanIslamicClock/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (OSError, ValueError):
        return False


def sync_prayer_schedule(gregorian: date, settings: dict, timeout: float = 4.0) -> dict | None:
    """Fetch a coordinate-based online prayer reference and return cached ISO values."""
    query = urllib.parse.urlencode({
        "latitude": settings["latitude"],
        "longitude": settings["longitude"],
        "method": 4,
        "school": 1 if settings.get("asr") == "Hanafi" else 0,
    })
    request = urllib.request.Request(
        f"https://api.aladhan.com/v1/timings/{gregorian.strftime('%d-%m-%Y')}?{query}",
        headers={"User-Agent": "ZishanIslamicClock/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        timings = payload["data"]["timings"]
        zone = ZoneInfo(settings["timezone"])
        result = {}
        for name in DAYLIGHT_EVENTS:
            raw = timings.get(name)
            if not raw:
                result[name] = None
                continue
            hour, minute = (int(part) for part in raw[:5].split(":"))
            result[name] = datetime(
                gregorian.year, gregorian.month, gregorian.day, hour, minute,
                tzinfo=zone).isoformat()
        return {"date": gregorian.isoformat(), "times": result,
                "source": "Online reference", "synced_at": datetime.now().isoformat(timespec="seconds")}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def bangla_date(gregorian: date) -> dict:
    """Convert a Gregorian date using Bangladesh's civil Bangla calendar."""
    starts = ((4, 14), (5, 15), (6, 15), (7, 16), (8, 16), (9, 16),
              (10, 17), (11, 16), (12, 16), (1, 15), (2, 14), (3, 15))
    names = ("Boishakh", "Joishtho", "Ashar", "Shraban", "Bhadro", "Ashwin",
             "Kartik", "Agrahayan", "Poush", "Magh", "Falgun", "Chaitra")
    year = gregorian.year - 593 if (gregorian.month, gregorian.day) >= (4, 14) else gregorian.year - 594
    candidates = []
    for index, (month, day) in enumerate(starts):
        for start_year in (gregorian.year - 1, gregorian.year, gregorian.year + 1):
            candidate = date(start_year, month, day)
            if candidate <= gregorian:
                candidates.append((candidate, index))
    start, month_index = max(candidates)
    month, start_day = starts[month_index]
    return {"day": (gregorian - start).days + 1, "month_name": names[month_index], "year": year}


def cache_prayer_schedule(day: date, settings: dict) -> dict:
    """Calculate and persist one local day's prayer schedule for offline use."""
    prayers = calculate_prayers(day, settings)
    sunrise = _sun_event(day, float(settings["latitude"]), float(settings["longitude"]), 90.833, True)
    if sunrise is not None:
        whole = int(sunrise)
        minute = int((sunrise - whole) * 60)
        second = int((((sunrise - whole) * 60) - minute) * 60)
        instant = datetime(day.year, day.month, day.day, whole, minute, second, tzinfo=ZoneInfo("UTC"))
        prayers["Sunrise"] = instant.astimezone(ZoneInfo(settings["timezone"]))
    else:
        prayers["Sunrise"] = None
    cache = settings.setdefault("prayer_cache", {})
    cache[day.isoformat()] = {
        name: value.isoformat() if value else None for name, value in prayers.items()
    }
    return prayers


def _storage_path() -> Path:
    root = os.environ.get("APPDATA") or str(Path.home())
    return Path(root) / "ZishanIslamicClock" / "settings.json"


def load_settings() -> dict:
    path = _storage_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = json.loads(json.dumps(DEFAULTS))
        merged.update(data)
        # Migrate the original Dhaka starter defaults to the requested Chattogram location.
        if (
            data.get("latitude") == 23.8103
            and data.get("longitude") == 90.4125
            and data.get("timezone") == "Asia/Dhaka"
            and data.get("city", "Dhaka, Bangladesh") == "Dhaka, Bangladesh"
        ):
            merged.update(DEFAULT_LOCATION)
        merged["adjustments"] = {**DEFAULTS["adjustments"], **data.get("adjustments", {})}
        ensure_prayer_events(merged)
        return merged
    except (OSError, ValueError, TypeError):
        return json.loads(json.dumps(DEFAULTS))


def save_settings(settings: dict) -> None:
    ensure_prayer_events(settings)
    path = _storage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def parse_clock_time(value: str) -> tuple[int, int]:
    """Parse a local HH:MM value and reject ambiguous or invalid input."""
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("time must use HH:MM")
    hour, minute = (int(part) for part in parts)
    if hour not in range(24) or minute not in range(60):
        raise ValueError("time is outside the 24-hour clock")
    return hour, minute


def ensure_prayer_events(settings: dict) -> dict:
    """Migrate old boolean prayer alarms into independent Azan/reminder events."""
    events = settings.setdefault("prayer_events", {})
    old = settings.get("prayer_alarms", {})
    for prayer in PRAYERS:
        prayer_events = events.setdefault(prayer, {})
        enabled = bool(old.get(prayer, False))
        prayer_events.setdefault("azan", {
            "enabled": enabled,
            "mode": "offset",
            "offset": 0,
            "time": "00:00",
        })
        prayer_events.setdefault("reminder", {
            "enabled": False,
            "mode": "offset",
            "offset": 30,
            "time": "00:00",
        })
        for event in EVENTS:
            item = prayer_events[event]
            item["enabled"] = bool(item.get("enabled", False))
            item["mode"] = item.get("mode", "offset") if item.get("mode") in ("offset", "fixed") else "offset"
            item["offset"] = int(item.get("offset", 0))
            item["time"] = str(item.get("time", "00:00"))
            parse_clock_time(item["time"])
    return settings


def prayer_event_time(base: datetime, event: dict) -> datetime:
    """Resolve one event without mutating its saved offset or fixed time."""
    if event.get("mode") == "fixed":
        hour, minute = parse_clock_time(event.get("time", "00:00"))
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base + timedelta(minutes=int(event.get("offset", 0)))


def scheduled_prayer_events(day: date, settings: dict) -> list[dict]:
    """Return enabled Azan/reminder occurrences for a local date, without duplicates."""
    ensure_prayer_events(settings)
    prayers = calculate_prayers(day, settings)
    result = []
    seen = set()
    for prayer in PRAYERS:
        base = prayers.get(prayer)
        if base is None:
            continue
        for event_name in EVENTS:
            event = settings["prayer_events"][prayer][event_name]
            if not event.get("enabled"):
                continue
            occurrence = prayer_event_time(base, event)
            identity = (prayer, event_name, occurrence.isoformat())
            if identity in seen:
                continue
            seen.add(identity)
            result.append({
                "id": f"{prayer}:{event_name}:{day.isoformat()}",
                "prayer": prayer,
                "event": event_name,
                "base": base,
                "time": occurrence,
                "mode": event.get("mode", "offset"),
                "offset": int(event.get("offset", 0)),
            })
    return sorted(result, key=lambda item: item["time"])


def next_general_alarm(alarm: dict, now: datetime) -> datetime | None:
    """Resolve the next enabled general alarm, honoring one-time and weekday repeats."""
    if not alarm.get("enabled"):
        return None
    try:
        hour, minute = parse_clock_time(alarm["time"])
    except (KeyError, TypeError, ValueError):
        return None
    repeat = sorted({int(day) for day in alarm.get("repeat", []) if int(day) in range(7)})
    for delta in range(8):
        candidate_day = now.date() + timedelta(days=delta)
        if repeat and candidate_day.weekday() not in repeat:
            continue
        candidate = now.replace(
            year=candidate_day.year, month=candidate_day.month, day=candidate_day.day,
            hour=hour, minute=minute, second=0, microsecond=0,
        )
        if candidate > now:
            return candidate
        if not repeat:
            return None
    return None


def _normalize_angle(value: float) -> float:
    return value % 360.0


def _sun_event(day: date, latitude: float, longitude: float, zenith: float, sunrise: bool) -> float | None:
    """NOAA solar declination/equation-of-time event; result is UTC decimal hours."""
    ordinal = day.timetuple().tm_yday
    gamma = 2 * math.pi / 365 * (ordinal - 1)
    equation = 229.18 * (
        0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma)
    )
    declination = math.asin(
        0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
    )
    cos_hour = (
        math.cos(math.radians(zenith))
        - math.sin(declination) * math.sin(math.radians(latitude))
    ) / (math.cos(declination) * math.cos(math.radians(latitude)))
    if not -1 <= cos_hour <= 1:
        return None
    hour_angle_minutes = math.degrees(math.acos(cos_hour)) * 4
    noon_minutes = 720 - (4 * longitude) - equation
    event_minutes = noon_minutes - hour_angle_minutes if sunrise else noon_minutes + hour_angle_minutes
    return (event_minutes / 60) % 24


def _solar_noon(day: date, longitude: float) -> float:
    """Approximate solar noon in UTC decimal hours."""
    ordinal = day.timetuple().tm_yday
    gamma = 2 * math.pi / 365 * (ordinal - 1)
    equation = 229.18 * (
        0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma)
    )
    return (720 - 4 * longitude - equation) / 60 % 24


def _asr_hour(day: date, latitude: float, longitude: float, shadow: int) -> float | None:
    """Calculate Asr from solar declination and the requested shadow factor."""
    ordinal = day.timetuple().tm_yday
    gamma = 2 * math.pi / 365 * (ordinal - 1)
    declination = 0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
    angle = math.degrees(math.atan(1 / (shadow + math.tan(abs(math.radians(latitude) - declination)))))
    cos_hour = (
        math.sin(math.radians(angle)) - math.sin(math.radians(latitude)) * math.sin(declination)
    ) / (math.cos(math.radians(latitude)) * math.cos(declination))
    if not -1 <= cos_hour <= 1:
        return None
    hour_angle = math.degrees(math.acos(cos_hour)) / 15
    return (_solar_noon(day, longitude) + hour_angle) % 24


def calculate_prayers(day: date, settings: dict) -> dict[str, datetime | None]:
    """Offline calculation using NOAA solar equations and Adhan-compatible method angles.

    The implementation intentionally labels results as calculated values. It supports
    method angles, Hanafi/Shafi'i Asr, high-latitude fallback, timezone conversion,
    and per-prayer minute adjustments, but is not a mosque timetable.
    """
    latitude = float(settings["latitude"])
    longitude = float(settings["longitude"])
    zone = ZoneInfo(settings["timezone"])
    fajr_angle, isha_angle = METHODS[settings["method"]]
    sunrise = _sun_event(day, latitude, longitude, 90.833, True)
    sunset = _sun_event(day, latitude, longitude, 90.833, False)
    fajr = _sun_event(day, latitude, longitude, 90 + fajr_angle, True)
    isha = _sun_event(day, latitude, longitude, 90 + isha_angle, False)
    dhuhr = _solar_noon(day, longitude)
    asr = _asr_hour(day, latitude, longitude, 2 if settings["asr"] == "Hanafi" else 1)
    values = {"Fajr": fajr, "Dhuhr": dhuhr, "Asr": asr, "Maghrib": sunset, "Isha": isha}
    if any(values[name] is None for name in PRAYERS):
        # High latitude fallback keeps a stable local time rather than returning invalid data.
        night = ((fajr if fajr is not None else 0) - (sunset if sunset is not None else 0)) % 24
        if settings["high_latitude"] == "Seventh of the night":
            fraction = 1 / 7
        elif settings["high_latitude"] == "Twilight angle":
            fraction = fajr_angle / 60
        else:
            fraction = 0.5
        if fajr is None and sunset is not None:
            values["Fajr"] = (sunset - night * fraction) % 24
        if isha is None and sunset is not None:
            values["Isha"] = (sunset + night * fraction) % 24
    result = {}
    for name in PRAYERS:
        utc_hour = values[name]
        if utc_hour is None:
            result[name] = None
            continue
        whole = int(utc_hour)
        minute = int((utc_hour - whole) * 60)
        second = int((((utc_hour - whole) * 60) - minute) * 60)
        instant = datetime(day.year, day.month, day.day, whole % 24, minute, second, tzinfo=ZoneInfo("UTC"))
        local = instant.astimezone(zone)
        while local.date() > day:
            local -= timedelta(days=1)
        while local.date() < day:
            local += timedelta(days=1)
        result[name] = local + timedelta(minutes=int(settings["adjustments"].get(name, 0)))
    return result


@dataclass
class GeneralAlarm:
    hour: int
    minute: int
    repeat: list[int] = field(default_factory=list)
    enabled: bool = True


class ClockApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.title("Zishan Islamic Clock")
        self.geometry("980x700")
        self.configure(bg="#050807")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.alarm_thread = threading.Thread(target=self._alarm_loop, daemon=True)
        self.alarm_thread.start()
        self._build()
        self._tick()

    def _build(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", background="#063d29", foreground="#f2fff8", padding=8)
        style.configure("TLabel", background="#050807", foreground="#f2fff8")
        style.configure("TNotebook", background="#050807")
        style.configure("TNotebook.Tab", background="#063d29", foreground="#f2fff8")
        self.clock_label = ttk.Label(self, font=("Segoe UI", 40), foreground="#00c878", background="#050807")
        self.clock_label.pack(pady=(18, 0))
        self.date_label = ttk.Label(self, font=("Segoe UI", 14))
        self.date_label.pack()
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=18)
        self._build_dashboard()
        self._build_alarms()
        self._build_settings()
        self._build_tools()
        self._build_about()

    def _build_dashboard(self) -> None:
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Prayer times")
        self.prayer_text = tk.Text(frame, bg="#050807", fg="#f2fff8", height=12, relief="flat", font=("Segoe UI", 16))
        self.prayer_text.pack(fill="x", padx=24, pady=24)
        ttk.Button(frame, text="Test alarm", command=lambda: self._ring("Test alarm")).pack(pady=5)
        ttk.Button(frame, text="Toggle prayer alarm", command=self._toggle_first_prayer).pack(pady=5)

    def _build_alarms(self) -> None:
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Alarms")
        ttk.Label(frame, text="General alarm time (24-hour HH:MM)").pack(anchor="w", padx=24, pady=(24, 4))
        self.general_time = ttk.Entry(frame)
        self.general_time.insert(0, "07:00")
        self.general_time.pack(fill="x", padx=24)
        self.general_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Enabled", variable=self.general_enabled).pack(anchor="w", padx=24, pady=8)
        ttk.Label(frame, text="Snooze minutes").pack(anchor="w", padx=24)
        self.general_snooze = ttk.Entry(frame)
        self.general_snooze.insert(0, str(self.settings["snooze"]))
        self.general_snooze.pack(fill="x", padx=24)
        ttk.Button(frame, text="Save general alarm", command=self._save_general_alarm).pack(pady=12)
        self.general_status = ttk.Label(frame, text=self._general_alarm_text())
        self.general_status.pack(anchor="w", padx=24)

    def _general_alarm_text(self) -> str:
        alarms = self.settings.get("general_alarms", [])
        if not alarms:
            return "No general alarm saved."
        alarm = alarms[0]
        return f"Saved: {alarm['time']} · {'enabled' if alarm['enabled'] else 'disabled'} · snooze {alarm['snooze']} min"

    def _save_general_alarm(self) -> None:
        try:
            hour, minute = (int(value) for value in self.general_time.get().split(":"))
            snooze = max(1, min(60, int(self.general_snooze.get())))
            if hour not in range(24) or minute not in range(60):
                raise ValueError
            self.settings["general_alarms"] = [{"time": f"{hour:02d}:{minute:02d}", "enabled": self.general_enabled.get(), "snooze": snooze}]
            save_settings(self.settings)
            self.general_status.configure(text=self._general_alarm_text())
        except ValueError:
            messagebox.showerror("General alarm", "Use HH:MM and a snooze value from 1 to 60.")

    def _build_settings(self) -> None:
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Settings")
        fields = {}
        for label, key in (("Latitude", "latitude"), ("Longitude", "longitude"), ("Time zone", "timezone")):
            ttk.Label(frame, text=label).pack(anchor="w", padx=24)
            entry = ttk.Entry(frame)
            entry.insert(0, str(self.settings[key]))
            entry.pack(fill="x", padx=24, pady=(0, 8))
            fields[key] = entry
        self.method = ttk.Combobox(frame, values=list(METHODS), state="readonly")
        self.method.set(self.settings["method"])
        self.method.pack(fill="x", padx=24, pady=6)
        self.asr = ttk.Combobox(frame, values=["Shafi'i", "Hanafi"], state="readonly")
        self.asr.set(self.settings["asr"])
        self.asr.pack(fill="x", padx=24, pady=6)
        self.fields = fields
        ttk.Button(frame, text="Save calculation settings", command=self._save_settings).pack(pady=12)
        ttk.Button(frame, text="Choose alarm sound", command=self._choose_sound).pack(pady=4)
        ttk.Button(frame, text="Toggle vibration", command=self._toggle_vibration).pack(pady=4)

    def _build_tools(self) -> None:
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Tools")
        self.analog = tk.Canvas(frame, width=320, height=320, bg="#050807", highlightthickness=0)
        self.analog.pack(side="left", padx=24, pady=24)
        controls = ttk.Frame(frame)
        controls.pack(side="left", fill="both", expand=True, padx=24, pady=24)
        self.stopwatch = ttk.Label(controls, text="Stopwatch 00:00.00", font=("Segoe UI", 20))
        self.stopwatch.pack(pady=8)
        self.stopwatch_start = None
        self.stopwatch_elapsed = 0
        ttk.Button(controls, text="Start / pause stopwatch", command=self._stopwatch_toggle).pack(pady=4)
        ttk.Button(controls, text="Reset stopwatch", command=self._stopwatch_reset).pack(pady=4)
        self.timer_entry = ttk.Entry(controls)
        self.timer_entry.insert(0, "300")
        self.timer_entry.pack(pady=8)
        ttk.Button(controls, text="Start timer (seconds)", command=self._start_timer).pack(pady=4)
        self.timer_label = ttk.Label(controls, text="Timer idle")
        self.timer_label.pack(pady=8)

    def _build_about(self) -> None:
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="About")
        ttk.Label(frame, text="Zishan Islamic Clock", font=("Segoe UI", 24)).pack(pady=(50, 8))
        ttk.Label(frame, text="Designed & Developed by Zishan AI Masters", font=("Segoe UI", 15)).pack()
        ttk.Label(frame, text="Al-Quran\nComing Soon", font=("Segoe UI", 18)).pack(pady=45)

    def _tick(self) -> None:
        now = datetime.now()
        self.clock_label.configure(text=now.strftime("%H:%M:%S"))
        self.date_label.configure(text=now.strftime("%A, %d %B %Y"))
        self._draw_analog(now)
        prayers = calculate_prayers(now.date(), self.settings)
        self.prayer_text.configure(state="normal")
        self.prayer_text.delete("1.0", "end")
        self.prayer_text.insert("end", "Calculated offline · adjusted values include manual minutes\n\n")
        for name in PRAYERS:
            value = prayers[name]
            self.prayer_text.insert("end", f"{name:<10} {value.strftime('%H:%M') if value else 'Unavailable'}\n")
        self.prayer_text.configure(state="disabled")
        if self.stopwatch_start is not None:
            self.stopwatch_elapsed = time.monotonic() - self.stopwatch_start
            self.stopwatch.configure(text=f"Stopwatch {self.stopwatch_elapsed // 60:02.0f}:{self.stopwatch_elapsed % 60:05.2f}")
        self.after(500, self._tick)

    def _draw_analog(self, now: datetime) -> None:
        self.analog.delete("all")
        cx, cy, radius = 160, 160, 125
        self.analog.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline="#00c878", width=4)
        values = ((now.hour % 12 + now.minute / 60, 12, 62, 8, "#f2fff8"),
                  (now.minute + now.second / 60, 60, 88, 5, "#f2fff8"),
                  (now.second, 60, 103, 2, "#00c878"))
        for value, divisor, length, width, color in values:
            angle = value / divisor * 2 * math.pi - math.pi / 2
            self.analog.create_line(cx, cy, cx + math.cos(angle) * length, cy + math.sin(angle) * length, fill=color, width=width)
        self.analog.create_oval(cx-6, cy-6, cx+6, cy+6, fill="#00c878", outline="")

    def _save_settings(self) -> None:
        try:
            self.settings["latitude"] = float(self.fields["latitude"].get())
            self.settings["longitude"] = float(self.fields["longitude"].get())
            if not -90 <= self.settings["latitude"] <= 90 or not -180 <= self.settings["longitude"] <= 180:
                raise ValueError
            ZoneInfo(self.fields["timezone"].get())
            self.settings["timezone"] = self.fields["timezone"].get()
            self.settings["method"] = self.method.get()
            self.settings["asr"] = "Hanafi" if self.asr.get() == "Hanafi" else "Shafi'i"
            save_settings(self.settings)
        except (ValueError, KeyError):
            messagebox.showerror("Invalid settings", "Enter valid coordinates and an IANA time zone such as Asia/Dhaka.")

    def _toggle_first_prayer(self) -> None:
        current = bool(self.settings["prayer_alarms"].get("Fajr"))
        self.settings["prayer_alarms"]["Fajr"] = not current
        save_settings(self.settings)

    def _choose_sound(self) -> None:
        chosen = filedialog.askopenfilename(filetypes=[("Audio files", "*.wav;*.mp3"), ("All files", "*.*")])
        if chosen:
            self.settings["sound"] = chosen
            save_settings(self.settings)

    def _toggle_vibration(self) -> None:
        self.settings["vibration"] = not self.settings["vibration"]
        save_settings(self.settings)

    def _ring(self, title: str) -> None:
        if winsound and self.settings.get("sound", "").lower().endswith(".wav"):
            winsound.PlaySound(self.settings["sound"], winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            self.bell()
        messagebox.showinfo("Zishan Islamic Clock", f"{title}\n\nSnooze is {self.settings['snooze']} minutes.")

    def _alarm_loop(self) -> None:
        last_key = None
        while True:
            now = datetime.now()
            key = now.strftime("%Y-%m-%d %H:%M")
            if now.second < 2 and key != last_key:
                prayers = calculate_prayers(now.date(), self.settings)
                for name, value in prayers.items():
                    if value and value.astimezone().strftime("%Y-%m-%d %H:%M") == key and self.settings["prayer_alarms"].get(name):
                        self.after(0, self._ring, name)
                for alarm in self.settings.get("general_alarms", []):
                    if alarm.get("enabled") and alarm.get("time") == now.strftime("%H:%M"):
                        self.after(0, self._ring, "General alarm")
                last_key = key
            time.sleep(1)

    def _stopwatch_toggle(self) -> None:
        if self.stopwatch_start is None:
            self.stopwatch_start = time.monotonic() - self.stopwatch_elapsed
        else:
            self.stopwatch_elapsed = time.monotonic() - self.stopwatch_start
            self.stopwatch_start = None

    def _stopwatch_reset(self) -> None:
        self.stopwatch_start = None
        self.stopwatch_elapsed = 0

    def _start_timer(self) -> None:
        try:
            seconds = max(1, int(self.timer_entry.get()))
        except ValueError:
            messagebox.showerror("Timer", "Enter a whole number of seconds.")
            return
        self.timer_deadline = time.monotonic() + seconds
        self._timer_tick()

    def _timer_tick(self) -> None:
        remaining = max(0, int(self.timer_deadline - time.monotonic()))
        self.timer_label.configure(text=f"Timer {remaining // 60:02d}:{remaining % 60:02d}")
        if remaining:
            self.after(250, self._timer_tick)
        else:
            self._ring("Timer finished")


if __name__ == "__main__":
    from premium_ui import PremiumClockApp
    PremiumClockApp().mainloop()
