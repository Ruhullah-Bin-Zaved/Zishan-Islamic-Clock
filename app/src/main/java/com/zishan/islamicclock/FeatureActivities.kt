package com.zishan.islamicclock

import android.app.Activity
import android.app.TimePickerDialog
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.CountDownTimer
import android.view.Gravity
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.NumberPicker
import android.widget.Switch
import android.widget.TextView
import java.time.LocalDate
import java.time.LocalTime

class GeneralAlarmsActivity : Activity() {
    private lateinit var list: LinearLayout
    private val store by lazy { GeneralAlarmStore(this) }
    override fun onCreate(state: Bundle?) { super.onCreate(state); render() }
    private fun render() {
        val root = screen("General alarms")
        list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(action("Add alarm") { createAlarm() })
        root.addView(list)
        setContentView(scroll(root))
        store.all().forEach { renderAlarm(it) }
    }
    private fun renderAlarm(alarm: GeneralAlarm) {
        val row = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(0, 10, 0, 10) }
        val toggle = Switch(this).apply {
            text = "%02d:%02d  repeat: %s".format(alarm.hour, alarm.minute, if (alarm.repeatDays.isEmpty()) "once" else alarm.repeatDays.sorted().joinToString(","))
            isChecked = alarm.enabled
            setOnCheckedChangeListener { _, checked -> store.save(alarm.copy(enabled = checked)); GeneralAlarmScheduler(this@GeneralAlarmsActivity).rescheduleAll() }
        }
        row.addView(toggle)
        row.addView(action("Edit") { editAlarm(alarm) })
        row.addView(action("Snooze ${alarm.snoozeMinutes} min · vibration ${if (alarm.vibration) "on" else "off"}") {
            val snooze = field(alarm.snoozeMinutes.toString(), "Snooze minutes")
            val vibration = CheckBox(this).apply { text = "Vibration"; isChecked = alarm.vibration }
            val options = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; addView(snooze); addView(vibration) }
            AlertDialog.Builder(this).setTitle("Alarm options").setView(options)
                .setPositiveButton("Save") { _, _ ->
                    val value = snooze.text.toString().toIntOrNull()?.coerceIn(1, 60) ?: 10
                    store.save(alarm.copy(snoozeMinutes = value, vibration = vibration.isChecked))
                    render()
                }.setNegativeButton("Cancel", null).show()
        })
        row.addView(action("Delete") { store.delete(alarm.id); GeneralAlarmScheduler(this).cancel(alarm.id); render() })
        list.addView(row)
    }
    private fun createAlarm() {
        val id = (store.all().maxOfOrNull { it.id } ?: 0) + 1
        editAlarm(GeneralAlarm(id, 7, 0))
    }
    private fun editAlarm(initial: GeneralAlarm) {
        TimePickerDialog(this, { _, h, m ->
            val names = arrayOf("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
            val selected = BooleanArray(7) { index -> index + 1 in initial.repeatDays }
            AlertDialog.Builder(this)
                .setTitle("Repeat days (none for one-time)")
                .setMultiChoiceItems(names, selected) { _, which, checked -> selected[which] = checked }
                .setPositiveButton("Save") { _, _ ->
                    val repeat = selected.mapIndexedNotNull { index, checked -> if (checked) index + 1 else null }.toSet()
                    store.save(initial.copy(hour = h, minute = m, repeatDays = repeat))
                    GeneralAlarmScheduler(this).rescheduleAll()
                    render()
                }
                .setNegativeButton("Cancel", null)
                .show()
        }, initial.hour, initial.minute, true).show()
    }
}

class PrayerAlarmSettingsActivity : Activity() {
    private val store by lazy { AlarmStore(this) }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val root = screen("Prayer alarm settings")
        PrayerCalculator.prayerNames.forEach { prayer ->
            val alarm = store.load(prayer) ?: PrayerAlarm(prayer, false, 0, 0)
            val toggle = Switch(this).apply {
                text = "$prayer alarm"
                isChecked = alarm.enabled
                setOnCheckedChangeListener { _, checked ->
                    store.save(alarm.copy(enabled = checked))
                    PrayerRescheduler(this@PrayerAlarmSettingsActivity).reschedule(LocalDate.now())
                }
            }
            root.addView(toggle)
            root.addView(action("Configure $prayer time") {
                TimePickerDialog(this, { _, h, m ->
                    store.save(alarm.copy(hour = h, minute = m, enabled = toggle.isChecked, manualTime = true))
                    PrayerRescheduler(this).reschedule(LocalDate.now())
                }, alarm.hour, alarm.minute, true).show()
            })
        }
        setContentView(scroll(root))
    }
}

class PrayerCalculationSettingsActivity : Activity() {
    private val store by lazy { PrayerSettingsStore(this) }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val current = store.load()
        val root = screen("Prayer calculation settings")
        val lat = field(current.latitude.toString(), "Latitude")
        val lon = field(current.longitude.toString(), "Longitude")
        root.addView(label("Manual coordinates"))
        root.addView(lat); root.addView(lon)
        root.addView(action("Cycle calculation method: ${current.method}") {
            val values = CalculationMethodOption.values()
            val next = values[(values.indexOf(store.load().method) + 1) % values.size]
            save(lat, lon, store.load().copy(method = next))
        })
        root.addView(action("Cycle Asr method: ${current.asrMethod}") {
            save(lat, lon, store.load().copy(asrMethod = if (store.load().asrMethod == AsrMethod.HANAFI) AsrMethod.SHAFI else AsrMethod.HANAFI))
        })
        root.addView(action("Cycle high-latitude rule: ${current.highLatitude}") {
            val values = HighLatitudeOption.values()
            save(lat, lon, store.load().copy(highLatitude = values[(values.indexOf(store.load().highLatitude) + 1) % values.size]))
        })
        PrayerCalculator.prayerNames.forEach { prayer ->
            val adjustment = field((current.adjustments[prayer] ?: 0).toString(), "$prayer adjustment minutes")
            root.addView(adjustment)
            root.addView(action("Save $prayer adjustment") {
                val next = store.load().adjustments.toMutableMap()
                next[prayer] = adjustment.text.toString().toIntOrNull() ?: 0
                save(lat, lon, store.load().copy(adjustments = next))
            })
        }
        root.addView(action("Save coordinates") { save(lat, lon, store.load()) })
        setContentView(scroll(root))
    }
    private fun save(lat: TextView, lon: TextView, current: PrayerSettings) {
        val result = runCatching { current.copy(latitude = lat.text.toString().toDouble(), longitude = lon.text.toString().toDouble()) }
        result.onSuccess { store.save(it); PrayerRescheduler(this).reschedule(LocalDate.now()) }
            .onFailure { lat.error = "Use valid numeric coordinates"; lon.error = "Use valid numeric coordinates" }
    }
}

class TimerActivity : Activity() {
    private lateinit var display: TextView
    private var timer: CountDownTimer? = null
    private var remaining = 0L
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val root = screen("Timer")
        val hours = number(0, 23); val minutes = number(5, 59); val seconds = number(0, 59)
        display = label("00:05:00", 36f)
        root.addView(display)
        root.addView(label("Hours / minutes / seconds"))
        root.addView(hours); root.addView(minutes); root.addView(seconds)
        root.addView(action("Start / Pause") {
            if (timer != null) { timer?.cancel(); timer = null } else {
                if (remaining <= 0) remaining = (hours.value * 3600L + minutes.value * 60L + seconds.value) * 1000
                timer = object : CountDownTimer(remaining, 1000) {
                    override fun onTick(value: Long) { remaining = value; display.text = format(value) }
                    override fun onFinish() {
                        remaining = 0
                        timer = null
                        display.text = "00:00:00"
                        startActivity(Intent(this@TimerActivity, RingingActivity::class.java).putExtra("prayer", "Timer"))
                    }
                }.start()
            }
        })
        root.addView(action("Cancel") { timer?.cancel(); timer = null; remaining = 0; display.text = "00:00:00" })
        setContentView(scroll(root))
    }
    private fun number(value: Int, maximum: Int) = NumberPicker(this).apply { minValue = 0; maxValue = maximum; this.value = value }
    private fun format(value: Long) = "%02d:%02d:%02d".format(value / 3_600_000, (value / 60_000) % 60, (value / 1000) % 60)
}

class SoundSettingsActivity : Activity() {
    private val preferences by lazy { getSharedPreferences("sound_settings", MODE_PRIVATE) }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val root = screen("Sound and vibration")
        root.addView(label("Alarm playback uses the Android alarm audio stream."))
        val vibration = Switch(this).apply {
            text = "Vibration"
            isChecked = preferences.getBoolean("vibration", true)
            setOnCheckedChangeListener { _, checked -> preferences.edit().putBoolean("vibration", checked).apply() }
        }
        root.addView(vibration)
        root.addView(label("Selected sound: ${preferences.getString("uri", "System default") ?: "System default"}"))
        root.addView(action("Choose audio file") {
            startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                type = "audio/*"
                addCategory(Intent.CATEGORY_OPENABLE)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            }, 42)
        })
        root.addView(action("Open system alarm sound settings") {
            startActivity(Intent(android.provider.Settings.ACTION_SOUND_SETTINGS))
        })
        setContentView(scroll(root))
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 42 && resultCode == RESULT_OK) {
            val uri: Uri = data?.data ?: return
            runCatching {
                contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
                preferences.edit().putString("uri", uri.toString()).apply()
            }.onFailure {
                preferences.edit().remove("uri").apply()
            }
        }
    }
}

class AboutActivity : Activity() {
    override fun onCreate(state: Bundle?) { super.onCreate(state); setContentView(scroll(screen("About").apply { addView(label("Zishan Islamic Clock", 22f)); addView(label("Designed & Developed by Zishan AI Masters", 18f)) })) }
}

class QuranActivity : Activity() {
    override fun onCreate(state: Bundle?) { super.onCreate(state); setContentView(scroll(screen("Al-Quran").apply { addView(label("Coming Soon", 24f)) })) }
}
