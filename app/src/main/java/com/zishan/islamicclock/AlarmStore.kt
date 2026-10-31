package com.zishan.islamicclock

import android.content.Context
import java.time.LocalDate

data class PrayerAlarm(
    val prayer: String,
    val enabled: Boolean = false,
    val hour: Int,
    val minute: Int,
    val soundUri: String? = null,
    val vibration: Boolean = true,
    val snoozeMinutes: Int = 10,
    val manualTime: Boolean = false
)

class AlarmStore(context: Context) {
    private val preferences = context.getSharedPreferences("alarm_settings", Context.MODE_PRIVATE)

    fun save(alarm: PrayerAlarm) {
        require(alarm.hour in 0..23 && alarm.minute in 0..59)
        require(alarm.snoozeMinutes in 1..60)
        preferences.edit().putString(alarm.prayer, listOf(
            alarm.enabled, alarm.hour, alarm.minute, alarm.soundUri ?: "", alarm.vibration, alarm.snoozeMinutes, alarm.manualTime
        ).joinToString("|")).apply()
    }

    fun load(prayer: String): PrayerAlarm? {
        val raw = preferences.getString(prayer, null) ?: return null
        val values = raw.split("|")
        if (values.size !in 6..7) return null
        return runCatching {
            PrayerAlarm(
                prayer = prayer,
                enabled = values[0].toBooleanStrict(),
                hour = values[1].toInt(),
                minute = values[2].toInt(),
                soundUri = values[3].ifBlank { null },
                vibration = values[4].toBooleanStrict(),
                snoozeMinutes = values[5].toInt(),
                manualTime = values.getOrNull(6)?.toBooleanStrict() ?: false
            ).also { require(it.hour in 0..23 && it.minute in 0..59 && it.snoozeMinutes in 1..60) }
        }.getOrNull()
    }

    fun configuredPrayers(): List<PrayerAlarm> =
        listOf("Fajr", "Dhuhr", "Asr", "Maghrib", "Isha").mapNotNull(::load)

    fun clear() = preferences.edit().clear().apply()
}
