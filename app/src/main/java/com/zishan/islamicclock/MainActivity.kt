package com.zishan.islamicclock

import android.Manifest
import android.app.Activity
import android.app.AlarmManager
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var clock: TextView
    private lateinit var timetable: TextView
    private lateinit var status: TextView
    private lateinit var alarmControls: LinearLayout
    private val settingsStore by lazy { PrayerSettingsStore(this) }
    private val alarmStore by lazy { AlarmStore(this) }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        buildUi()
        refresh()
        requestRuntimePermissions()
    }

    private fun buildUi() {
        clock = TextView(this).apply { textSize = 42f; gravity = Gravity.CENTER }
        timetable = TextView(this).apply { textSize = 18f; setPadding(24, 16, 24, 16) }
        status = TextView(this).apply { setPadding(24, 16, 24, 16) }
        val test = Button(this).apply {
            text = "Test alarm"
            setOnClickListener {
                startActivity(Intent(this@MainActivity, RingingActivity::class.java).putExtra("prayer", "Test alarm"))
            }
        }
        val location = Button(this).apply {
            text = "Use current location"
            setOnClickListener { requestLocation() }
        }
        val settings = Button(this).apply {
            text = "Prayer settings"
            setOnClickListener { startActivity(Intent(this@MainActivity, PrayerCalculationSettingsActivity::class.java)) }
        }
        val diagnostics = Button(this).apply {
            text = "Alarm diagnostics"
            setOnClickListener { showDiagnostics() }
        }
        val navigation = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(action("Analog clock") { startActivity(Intent(this@MainActivity, AnalogClockActivity::class.java)) })
            addView(action("General alarms") { startActivity(Intent(this@MainActivity, GeneralAlarmsActivity::class.java)) })
            addView(action("Prayer alarm settings") { startActivity(Intent(this@MainActivity, PrayerAlarmSettingsActivity::class.java)) })
            addView(action("Prayer calculation settings") { startActivity(Intent(this@MainActivity, PrayerCalculationSettingsActivity::class.java)) })
            addView(action("Stopwatch") { startActivity(Intent(this@MainActivity, StopwatchActivity::class.java)) })
            addView(action("Timer") { startActivity(Intent(this@MainActivity, TimerActivity::class.java)) })
            addView(action("Sound and vibration") { startActivity(Intent(this@MainActivity, SoundSettingsActivity::class.java)) })
            addView(action("About") { startActivity(Intent(this@MainActivity, AboutActivity::class.java)) })
            addView(action("Al-Quran") { startActivity(Intent(this@MainActivity, QuranActivity::class.java)) })
        }
        val about = TextView(this).apply {
            text = "About\nZishan Islamic Clock\nDesigned & Developed by Zishan AI Masters\n\nAl-Quran\nComing Soon"
            textSize = 18f
            setPadding(24, 24, 24, 24)
        }
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(16, 32, 16, 32)
            addView(clock)
            addView(timetable)
            alarmControls = LinearLayout(this@MainActivity).apply { orientation = LinearLayout.VERTICAL }
            addView(alarmControls)
            addView(status)
            addView(location)
            addView(settings)
            addView(diagnostics)
            addView(test)
            addView(navigation)
            addView(about)
        }
        setContentView(ScrollView(this).apply { addView(content) })
        buildAlarmControls()
    }

    private fun buildAlarmControls() {
        alarmControls.removeAllViews()
        PrayerCalculator.prayerNames.forEach { prayer ->
            alarmControls.addView(Button(this).apply {
                tag = prayer
                setOnClickListener { toggleAlarm(prayer) }
            })
        }
    }

    private fun refresh() {
        handler.removeCallbacksAndMessages(null)
        clock.text = java.time.ZonedDateTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss"))
        val settings = settingsStore.load()
        val prayers = PrayerCalculator().calculate(LocalDate.now(), settings)
        timetable.text = buildString {
            append("Today · ${LocalDate.now()}\n")
            prayers.forEach { prayer ->
                val enabled = alarmStore.load(prayer.name)?.enabled == true
                append("${prayer.name}: ${prayer.adjusted.format(DateTimeFormatter.ofPattern("HH:mm"))}")
                append(if (enabled) "  • alarm on" else "  • alarm off")
                append("\n")
            }
        }
        alarmControls.children().forEach { button ->
            val prayer = button.tag as String
            val enabled = alarmStore.load(prayer)?.enabled == true
            (button as Button).text = "$prayer alarm: ${if (enabled) "ON" else "OFF"}"
        }
        status.text = "Location: %.4f, %.4f\nTime zone: %s\nMethod: %s · Asr: %s".format(
            settings.latitude, settings.longitude, settings.zoneId, settings.method, settings.asrMethod
        )
        handler.postDelayed({ refresh() }, 1000)
    }

    private fun requestRuntimePermissions() {
        val permissions = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= 33) permissions += Manifest.permission.POST_NOTIFICATIONS
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            permissions += Manifest.permission.ACCESS_FINE_LOCATION
        }
        if (permissions.isNotEmpty()) requestPermissions(permissions.toTypedArray(), 100)
    }

    private fun requestLocation() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED &&
            checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION), 101)
            return
        }
        val manager = getSystemService(LocationManager::class.java)
        val location: Location? = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
            .mapNotNull { provider -> runCatching { manager.getLastKnownLocation(provider) }.getOrNull() }
            .minByOrNull { it.time * -1 }
        if (location == null) {
            status.text = "No cached location available. Use manual coordinates in Prayer settings."
            return
        }
        val current = settingsStore.load()
        settingsStore.save(current.copy(
            latitude = location.latitude,
            longitude = location.longitude,
            zoneId = ZoneId.systemDefault().id
        ))
        PrayerRescheduler(this).reschedule(LocalDate.now())
        refresh()
    }

    private fun toggleAlarm(prayer: String) {
        val current = alarmStore.load(prayer)
        val next = !(current?.enabled ?: false)
        val time = PrayerCalculator().calculate(LocalDate.now(), settingsStore.load())
            .first { it.name == prayer }.adjusted
        alarmStore.save(PrayerAlarm(prayer, next, time.hour, time.minute, snoozeMinutes = current?.snoozeMinutes ?: 10))
        PrayerRescheduler(this).reschedule(LocalDate.now())
        refresh()
    }

    private fun showDiagnostics() {
        val manager = getSystemService(AlarmManager::class.java)
        val exact = Build.VERSION.SDK_INT < Build.VERSION_CODES.S || manager.canScheduleExactAlarms()
        status.text = "Exact alarm access: ${if (exact) "available" else "denied or revoked"}\n" +
            "Full-screen intent eligibility is controlled by Android.\n" +
            "Force-stop and OEM battery restrictions cannot be bypassed."
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && !exact) {
            startActivity(Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM))
        }
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }
}

private fun LinearLayout.children(): List<android.view.View> =
    (0 until childCount).map(::getChildAt)
