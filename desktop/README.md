# Windows desktop version

This is a separate Python/Tkinter desktop target. It does not replace the Android project. It launches the premium sidebar/card interface in `premium_ui.py`, with a time/prayer-focused dashboard containing live digital/analog time, Gregorian/Bangla/Hijri dates, next-prayer countdown, prayer cards, and a prayer timeline. It also includes calculation settings, independent editable Azan/reminder events, recurring or one-time general alarms, WAV/MP3 sound selection, vibration preference, snooze setting, timer, stopwatch with laps, Focus Session, Tasbih Counter, Quick Notes, About, and AI Quran Coming Soon page.

## Run on Windows

Python 3.11+ is recommended. Tkinter is included in the standard Windows Python installer.

The easiest way is to double-click **Start Zishan Islamic Clock.bat** in the project folder. The background launcher is also available for startup use and follows the same maximized startup policy.

The main digital clock uses 12-hour format with AM/PM. General alarm entry uses hour/minute spin controls and a separate AM/PM selector, so you do not need to type a 24-hour time.

The Settings page uses a mouse-wheel canvas without a visible scrollbar, so location, calculation, adjustments, sound, vibration, sync, and snooze controls remain accessible on laptop-sized windows. The Tools page uses a compact Focus card above the Stopwatch/Timer and Tasbih/Quick Notes grid; a hidden canvas scroll region is only available on very small windows.

```powershell
cd path\to\ZishanIslamicClock
python desktop\zishan_clock.py
```

Run the offline calculation tests:

```powershell
python -m unittest discover -s desktop -p "test_*.py"
```

Settings are stored at `%APPDATA%\ZishanIslamicClock\settings.json`. The starter location is **Chattogram, Bangladesh** (`22.3569, 91.7832`) with the Bangladesh timezone (`Asia/Dhaka`). Change the city label and coordinates in Settings if you are elsewhere; the app does not silently detect or track GPS.

## Windows limitations

The desktop target keeps alarms alive while the app is running. The active UI refreshes once per second and the alarm safety monitor checks every five seconds, avoiding a tight CPU loop. The audio picker accepts both `.wav` and `.mp3`: WAV is played directly by Windows, while MP3 opens in the Windows default audio player. It does not bypass Windows sleep, process termination, or notification policy.

To start it automatically after Windows login:

1. Right-click **Start Zishan Islamic Clock - Background.bat** and choose **Create shortcut**.
2. Press `Win+R`, type `shell:startup`, and press Enter.
3. Move or copy the shortcut into that Startup folder.

The launcher opens the app using the same maximized startup policy. A packaged EXE is created only when `Build Windows EXE.bat` completes successfully on Windows.

## Share as one Windows application

For the easiest sharing experience, double-click **Build Windows EXE.bat** in the project folder. It installs PyInstaller for your Windows user account if needed, then creates:

```text
dist\ZishanIslamicClock.exe
```

Send that EXE to your friend. They do not need Android, Gradle, or the project source. On first launch, Windows SmartScreen may show a warning because the EXE is not digitally signed; choose **More info** and verify that you received the file from you before selecting **Run anyway**. This build still needs to remain open for desktop alarms and does not wake a sleeping laptop.

Settings are stored separately per Windows user in `%APPDATA%\ZishanIslamicClock\settings.json`. A selected audio file is not embedded in the EXE, so send the audio file separately or let your friend choose their own file in Settings.

Prayer times use an offline NOAA-style solar calculation with the documented Adhan-compatible method angles, Hanafi/Shafi'i Asr shadow, high-latitude fallback, time-zone conversion, and manual adjustments. They are calculated values, not mosque-approved timetables.

The main dashboard uses a custom dark sidebar/card layout rather than default ttk tabs. The app can be resized above 940x640; the prayer cards, clock card, and tool cards expand with the window. GUI appearance and Windows alarm delivery still require a real interactive Windows session.

Prayer event settings support:

- **Offset mode:** saved minutes remain relative to each day's calculated base prayer time.
- **Fixed mode:** saved local `HH:MM` remains unchanged when the calculated base changes.
- Azan and reminder enablement, mode, and time/offset are independent per prayer.

The active desktop monitor prevents duplicate occurrences during a running session and honors repeat weekdays for general alarms. The stopwatch uses a monotonic clock with a smooth approximately 20ms display animation and continues measuring while another page is open. Focus tracks an editable daily goal (default 8 hours) plus Today, This week, and All time study totals. It does not provide a Windows service or wake the machine from sleep.

Tools uses a compact Fluent-inspired hierarchy: a complete Focus Session card with Study/Break timers, progress ring, Start Study/Break, Pause, Reset, Save Times, editable session durations, an editable daily goal (default 8 hours), statistics, streak, separate Study/Break sounds, enable/disable switches, and 0–100 volume controls, followed by equal Stopwatch/Timer and Tasbih/Quick Notes cards. Study targets support 1–1,440 minutes, and Focus reports elapsed progress plus persistent Today, This week, and All time totals; a 12-hour target is tracked against 12 hours rather than a fixed 25-minute assumption. Focus fullscreen includes a subtle native canvas cat companion: it walks quietly during Study and shows a snack/mischief scene during Break without external assets or high-frequency animation. Selected sounds loop during their phase and stop on pause/reset; WAV and MP3 playback use Windows media support where available. Stopwatch retains Start, Pause, Lap, and Reset; Timer retains hour/minute/second selectors, five presets, and Start/Pause/Reset; Tasbih retains +, −, Reset, current count, daily count, and double-click +10. The app starts maximized, remembers the last geometry, and note text autosaves locally while typing with a saved-time indicator. Tools uses an invisible canvas scroll region only when the compact layout exceeds a very small window; there is no visible scrollbar.

Hijri dates use a hybrid path. The default local civil calculation works offline, with English transliteration as the display default; Arabic and Both are available in Settings. On startup and during the evening maintenance check, the selected source is attempted and the result is cached locally. Saudi Umm Al-Qura can sync through Aladhan when internet is available. If Bangladesh Official or Global Moon Sighting has no supported endpoint, the app may use an explicitly labelled `Online reference fallback`; it never presents that fallback as the selected official source or as universally/100% accurate.

The desktop scheduler regenerates the current day's prayer cache at or after 12:01 AM and performs the evening Hijri/prayer maintenance check at or after 8:00 PM while the app process is running. Cached prayer times, Hijri data, Bangla dates, and countdowns continue offline. Windows desktop apps cannot run this maintenance after the process is terminated or the device is asleep; launch the app again to catch up.

Prayer calculations remain offline and do not transmit coordinates by default. Settings offers an explicit network sync: when reachable, a coordinate-based online prayer reference and the selected supported Hijri reference are cached locally; failed requests fall back to local calculation. No account, analytics, advertising, or weather network integration is used, and the dashboard intentionally contains no weather widget.
