# Zishan Islamic Clock

## Windows desktop application

The repository includes a separate Windows-friendly Python/Tkinter application in [desktop](./desktop). It does not replace or delete the Android project.

Run it from PowerShell:

```powershell
cd path\to\ZishanIslamicClock
python desktop\zishan_clock.py
```

Or double-click [Start Zishan Islamic Clock.bat](./Start%20Zishan%20Islamic%20Clock.bat). The background launcher uses the same maximized startup policy so the app always opens consistently.

Run the desktop tests:

```powershell
python -m unittest discover -s desktop -p "test_*.py"
```

The desktop app stores settings in `%APPDATA%\ZishanIslamicClock\settings.json`. Its starter location is Chattogram (`22.3569, 91.7832`, timezone `Asia/Dhaka`); update City/Latitude/Longitude in Settings if needed. It uses local offline solar calculations, does not require an Android phone, and has no ads, analytics, accounts, or tracking. Windows alarms are best-effort while the app process is running; Windows sleep, process termination, and notification policy can prevent delivery. For startup, create a shortcut to the command in `shell:startup` or configure Windows Task Scheduler.

The desktop target uses optional online Hijri/prayer reference sync from Settings when internet is available; local calculation and cached data remain available offline. It does not continuously track GPS.

The main clock is shown in 12-hour AM/PM format. General alarms use hour/minute controls plus a separate AM/PM selector. The dashboard prioritizes time, prayer cards/timeline, and Gregorian/Bangla/Hijri dates. Dashboard full-screen mode is available and exits with `Esc`. Tools includes an editable 25-minute study/5-minute break cycle with a separate sound setting from Azan audio.

Alarm audio accepts WAV and MP3 files. WAV playback is controlled directly by the app; MP3 playback uses the Windows default audio player, so its independent player window/volume behavior is controlled by Windows.

For automatic startup, create a shortcut to the launcher `.bat`, press `Win+R`, open `shell:startup`, and place the shortcut there. This is a normal user-level Windows startup shortcut; it does not install a service or request administrator access. The app opens maximized by design.

To share one Windows application, double-click [Build Windows EXE.bat](./Build%20Windows%20EXE.bat). After it completes, send `dist\ZishanIslamicClock\ZishanIslamicClock.exe`; your friend can double-click it without Android or the source project. PyInstaller is not bundled, so the script installs it for the current Windows user when needed.

The desktop UI is a custom dark sidebar/card interface with a midnight background, emerald primary accent, restrained gold labels, responsive prayer cards, a live analog clock with numerals and tick marks, and a next-prayer countdown. Prayer Azan/reminder events can be independently enabled and configured in offset or fixed-clock mode; general alarms support edit/delete, one-time alarms, and selected weekdays.

Native Android Kotlin app focused on reliable, local prayer alarms and offline prayer-time calculation.

## Current implementation

- Prayer times use Adhan Java `1.2.1` (`com.batoulapps.adhan:adhan`), a maintained, MIT-licensed library from the Batoulapps project. It uses local Gregorian date components, supplied coordinates, and the device time zone. The app does not label results as mosque-approved or universally accurate.
- Supported calculation methods currently exposed: Muslim World League, Karachi, Egyptian, North America/ISNA, and Singapore.
- Supported Asr schools: Hanafi and Shafi'i.
- Supported high-latitude rules: middle of night, seventh of night, and twilight angle.
- Manual per-prayer minute adjustments are represented and validated in `PrayerSettings`; the UI currently cycles calculation method and exposes local prayer-alarm toggles.
- Location is permission-gated and uses a cached GPS/network location only. No continuous tracking is performed. Manual/default coordinates remain available when no cached location exists.
- Results are calculated offline. Calculated and adjusted values are kept separate in `PrayerTime`; mosque timetables are not imported or represented as verified app calculations.
- Native screens now cover analog/full-screen clock, general alarms, prayer alarm controls, prayer calculation settings, stopwatch, timer, sound/system settings, About, and Al-Quran.

## Important limitations

`AlarmManager` cannot bypass force-stop, denied permissions, Doze/OEM restrictions, or unavailable full-screen-intent eligibility. Exact alarms fall back to an inexact `setAndAllowWhileIdle` alarm when exact-alarm access is unavailable. Delivery may still be delayed by device policy.

The current project intentionally does not claim calculation accuracy: a verified prayer-calculation library and reference fixtures must be selected before production use. Calculated, manually adjusted, and mosque-supplied values must remain separate in the eventual settings model.

## Alarm lifecycle

1. User saves an enabled prayer alarm.
2. The scheduler rejects past timestamps and uses a stable prayer request code.
3. `BOOT_COMPLETED`, locked boot, time, and time-zone changes trigger recalculation/rescheduling.
4. The receiver opens a dedicated ringing activity; ordinary reminder notifications are not created.
5. Dismissal releases vibration, media, notification, and audio-focus resources. Snooze schedules one future occurrence.
6. Exact-alarm access and full-screen intent eligibility must be diagnosed in-app; neither is silently assumed.

## Permissions

- `SCHEDULE_EXACT_ALARM`: best-effort exact prayer alarm timing; user can deny/revoke it.
- `USE_FULL_SCREEN_INTENT`: eligible alarm UI while locked; Android may restrict eligibility.
- `RECEIVE_BOOT_COMPLETED`: restore alarms after reboot.
- `VIBRATE`: optional vibration.
- `ACCESS_COARSE_LOCATION` / `ACCESS_FINE_LOCATION`: only for an explicit current-location action; manual/default coordinates work without it.
- `POST_NOTIFICATIONS`: Android may require this for the system-managed alarm notification. Ordinary prayer reminder notifications are not created.

No analytics, advertising SDK, continuous location tracking, or account is included. The desktop sync action makes only the documented Hijri/prayer reference requests and falls back locally when unavailable. App data clearing and uninstall remove local settings and scheduled alarms.

## Build and validation status

### Simplest Windows setup when this workspace is available

Install a trusted JDK 17 distribution and Android Studio from the official Android developer site. In Android Studio SDK Manager, install Android SDK Platform 35 and Build-Tools. Then open this folder as an Android Studio project and run:

```powershell
gradle.bat :app:testDebugUnitTest
gradle.bat :app:assembleDebug
```

This repository currently has no Gradle Wrapper, so Android Studio's configured Gradle or a trusted Gradle installation is required. If the project is imported into Android Studio, use its bundled JDK 17 and let it sync dependencies from Maven Central.

| Check | Status | Evidence / remaining risk |
|---|---|---|
| Source inspection | Passed | Existing source, manifest, Gradle files, README, and QA checklist inspected |
| Source implementation | Static only | Calculator, settings, UI, notification, and lifecycle code added |
| Review fixes | Source-reviewed | Pending-alarm replacement, one-time alarms, per-alarm ringing settings, audio-player state, timer state, URI handling, and full-screen exit flow corrected |
| Gradle build | Blocked | Windows environment has no Java/JDK, Gradle, Gradle Wrapper, Android SDK, or ADB |
| Unit tests | Not run | JUnit test source added; no runnable JVM toolchain is installed |
| Instrumentation tests | Not run | Requires Android SDK/device |
| Locked/off-screen alarm | Not run | Requires physical/emulated Android device |
| Reboot/time-zone/Doze/OEM matrix | Not run | Requires device matrix and permission states |
| Security/dependency audit | Not run | Dependency tooling unavailable |

## Prioritized remaining work

1. Run the Gradle wrapper/build on a machine with JDK 17 and Android SDK 35, then fix any dependency/API issues found by the compiler.
2. Add trusted numerical Adhan test-data fixtures with published tolerances; current tests validate settings, local date/zone shape, and adjustment behavior without fabricating prayer-time expectations.
3. Add backup import/export with schema validation and destructive-action confirmation.
4. Run the complete physical-device alarm matrix, including Android notification/full-screen eligibility and OEM battery policies.
