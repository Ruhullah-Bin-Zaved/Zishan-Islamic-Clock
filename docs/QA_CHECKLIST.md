# Alarm and product QA matrix

Run this checklist on each supported Android version and at least one device with aggressive OEM battery management. A row is only marked passed after direct observation.

| Scenario | Expected result | Status |
|---|---|---|
| Screen locked | Eligible alarm opens ringing UI or documented OS fallback | Not run |
| Screen off | Device wakes only as permitted by Android policy | Not run |
| App backgrounded | Alarm receiver still runs | Not run |
| App swiped away | Alarm remains scheduled | Not run |
| OS process killed | Alarm receiver starts without app process state | Not run |
| Device reboot | Boot receiver recalculates and reschedules enabled future alarms | Not run |
| Date changed | Past alarms are rejected; next date is recalculated | Not run |
| Clock changed | Existing alarms are rebuilt from current local date/time | Not run |
| Time-zone changed | Times are recalculated in the new system zone | Not run |
| DST transition | No duplicate or past occurrence | Not run |
| Battery Saver / Doze | `setAndAllowWhileIdle` behavior is observed and delays documented | Not run |
| Exact permission denied/revoked | Inexact fallback and diagnostic are visible | Not run |
| Full-screen unavailable | No claim of bypass; user sees normal supported behavior | Not run |
| Dismiss | Playback, vibration, focus, and activity are cleaned up | Not run |
| Snooze | One future occurrence is scheduled and duplicate is not created | Not run |
| Cancel/reschedule | Stable request code removes stale occurrence | Not run |
| Location changed | Current-location action stores coordinates and reschedules | Static only |
| Calculation method changed | Method cycle stores setting and reschedules enabled prayers | Static only |
| Test alarm | User can start ringing UI immediately | Static only |
| Offline | Adhan calculation has no network dependency | Static only |
| Settings restart/update | Local settings survive ordinary restart/update | Not run |
| Analog/full-screen clock | Analog hands update once per second and immersive mode opens | Static only |
| General alarms | Create/edit/delete/toggle and repeat-day selection persist locally | Source-reviewed |
| Prayer alarm settings | Five prayer toggles and times persist and reschedule | Static only |
| Stopwatch | Start, pause, resume, reset, and laps work | Source-reviewed |
| Timer | Start, pause, cancel, and ring-on-finish work | Source-reviewed |
| Data clear/uninstall | Local settings and alarms are removed | Not run |
| Accessibility | Controls have readable labels, contrast, and large touch targets | Not run |
| Responsive layout | Ringing UI remains usable across screen sizes | Not run |
| Audio interruption/routing | Focus is requested and released; route behavior is observed | Source-reviewed; device not run |

Known gaps before production: trusted Adhan reference fixtures with tolerances, document-picker custom audio, richer per-alarm snooze/vibration controls, backup import/export, exact full-screen notification policy handling, and automated/device test execution. No device or production build result is claimed in this environment.

## Windows desktop target

| Check | Status | Evidence |
|---|---|---|
| Python syntax compilation | Passed | `python -m py_compile desktop\zishan_clock.py desktop\test_zishan_clock.py` |
| Offline prayer unit tests | Passed | 3 unittest cases passed |
| Prayer smoke calculation | Passed | Five non-null prayers produced for the current date |
| Tkinter GUI launch | Not run | Headless agent environment has no interactive desktop session |
| Premium sidebar/card visual layout | Source-reviewed | Custom `desktop\premium_ui.py`; no default ttk notebook is used by the launcher |
| Dark/emerald/gold visual system | Source-reviewed | Centralized `BG`, `CARD`, `EMERALD`, `GOLD`, `TEXT`, and `MUTED` colors |
| Dashboard next-prayer countdown | Source-reviewed | Dashboard derives next future prayer from `calculate_prayers` |
| Prayer Azan/reminder offset mode | Passed | Unit test verifies saved offset is applied to the calculated base |
| Prayer fixed-clock mode | Passed | Unit test verifies fixed `HH:MM` is unchanged across dates |
| Independent prayer event identities | Passed | Unit test verifies Azan/reminder produce separate non-duplicate IDs |
| General one-time/repeating resolution | Passed | Unit test verifies one-time past alarm is skipped and weekday alarm resolves |
| General alarm edit/delete/toggle | Source-reviewed | Active UI has Edit, Delete confirmation, and Enabled controls |
| Stopwatch laps | Source-reviewed | Active Tools page records monotonic lap values |
| Smooth stopwatch hundredths | Passed | Dedicated 20ms animation loop plus monotonic elapsed time; navigation smoke test passed |
| 12-hour main clock | Source-reviewed | Dashboard formats digital time as hour/minute/seconds with AM/PM |
| AM/PM alarm picker | Source-reviewed | General alarm uses hour/minute Spinboxes and separate AM/PM selector |
| Dashboard full-screen clock | Source-reviewed | Full-screen toggle plus Escape exit binding |
| Study/break cycle | Source-reviewed | Focus Session hero exposes study/break minutes, Save times, Start Focus, Start break, Pause, Reset, separate sound, and focus fullscreen |
| Tools productivity layout | Source-reviewed | Tools uses a Focus Session card, compact Stopwatch/Timer tools, and Tasbih/Quick Note tools; duplicate headings are removed |
| Tools Fluent visual hierarchy | Source-reviewed | Hero-first layout removes duplicate summary cards and quick-action dock while preserving tool controls |
| Tools hover feedback | Source-reviewed | Cards and buttons bind enter/leave highlight states with emerald/gold accents |
| Focus progress ring | Source-reviewed | Canvas ring updates with active study/break progress and session count |
| Timer preset chips | Source-reviewed | 1, 5, 10, 25, and 45 minute presets populate timer selectors |
| Tasbih keyboard/double-click controls | Source-reviewed | Ctrl+Shift+T increments; card double-click increments by 10; +/- and reset persist |
| Tools smooth scrolling | Source-reviewed | Tools content uses an invisible canvas scroll region and mouse-wheel binding; no visible scrollbar is rendered |
| Dashboard hierarchy | Source-reviewed | Time/prayer-first hero, active prayer cards, timeline, analog clock, and compact actions |
| Bangla calendar date | Passed | `bangla_date` helper returns the Bangladesh civil calendar month/year |
| Offline Hijri date | Passed | `offline_hijri` returns a civil lunar date without network access |
| Hijri source/cache fallback | Source-reviewed | Optional Saudi Umm Al-Qura sync, evening refresh, and cache/local fallback remain visible with an explicit source label |
| Tasbih persistence | Source-reviewed | Count and reset actions save locally |
| Quick Notes persistence | Source-reviewed | Note editor saves locally through Save note |
| Hijri date | Passed | Offline anchored lunar calculation displays English transliteration by default and supports Arabic/Both |
| Prayer schedule cache | Passed | Current day cache includes Fajr, Sunrise, Dhuhr, Asr, Maghrib, and Isha |
| Weather removal | Passed | No weather widget or weather integration remains in the desktop UI |
| Tools compact scroll layout | Source-reviewed | Complete Focus Session remains above the Stopwatch/Timer and Tasbih/Quick Notes two-by-two grid; overflow uses mouse-wheel only with no visible scrollbar |
| Quick Notes autosave | Source-reviewed | Key-release debounce, explicit Save, startup restore, saved timestamp, and close-time save are wired |
| Maximized startup | Source-reviewed | Startup calls `state("zoomed")` and persists the last window geometry |
| Tool control preservation | Source-reviewed | Focus, Stopwatch, Timer, Tasbih, and Notes retain all requested controls without a Tools scrollbar |
| Focus phase sounds | Source-reviewed; device not run | Separate Study/Break files, enable switches, volume controls, looping, phase switching, pause/reset cleanup are wired; actual audible MP3/WAV playback remains device-dependent |
| Settings scrolling | Source-reviewed | Settings uses a mouse-wheel canvas with no visible scrollbar and resizes its inner content |
| Timer pause/resume/reset | Source-reviewed | Active Tools page uses monotonic deadline and explicit controls |
| Analog numerals and tick marks | Source-reviewed | Active dashboard draws 1–12, major/minor ticks, and three hands |
| Active alarm monitor | Source-reviewed | Active premium app checks prayer/general occurrences every five seconds and deduplicates session keys |
| Low-usage refresh behavior | Source-reviewed | Clock refreshes once per second; alarm safety monitor runs every five seconds |
| Visible Windows launcher | Source-reviewed | `Start Zishan Islamic Clock.bat` uses `pythonw.exe` and repository-relative paths |
| Background launcher | Source-reviewed | `Start Zishan Islamic Clock - Background.bat` follows the maximized startup policy |
| Windows login startup | Not run | Requires user-created shortcut in `shell:startup` |
| WAV/MP3 audio selection | Source-reviewed | Settings picker accepts `.wav` and `.mp3`; WAV is native, MP3 delegates to Windows default player |
| EXE packaging | Not run | `Build Windows EXE.bat` is provided; actual packaging requires PyInstaller on Windows |
| Default location | Passed | Chattogram coordinates `22.3569, 91.7832`, timezone `Asia/Dhaka`; unit test covers defaults |
| Alarm snooze/dismiss controls | Source-reviewed | Active ringing dialog stops WAV playback on dismiss and schedules an in-app snooze |
| Desktop unit suite | Passed | `python -m unittest discover -s desktop -p "test_*.py"` — 12 tests passed |
| Desktop page construction smoke test | Passed | Dashboard, Prayer alarms, General alarms, Tools, Settings, About, and Al-Quran constructed |
| Windows alarm delivery after sleep/process kill | Not run | Requires a Windows laptop session |
| Windows startup/task scheduler | Not run | Requires local Windows configuration |
| Packaged EXE | Not run | PyInstaller is not installed; run from Python or install PyInstaller locally |
