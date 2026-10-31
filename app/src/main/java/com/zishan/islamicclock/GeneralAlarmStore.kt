package com.zishan.islamicclock

import android.content.Context

data class GeneralAlarm(
    val id: Int,
    val hour: Int,
    val minute: Int,
    val repeatDays: Set<Int> = emptySet(),
    val enabled: Boolean = true,
    val snoozeMinutes: Int = 10,
    val vibration: Boolean = true,
    val soundUri: String? = null
)

class GeneralAlarmStore(context: Context) {
    private val preferences = context.getSharedPreferences("general_alarms", Context.MODE_PRIVATE)

    fun all(): List<GeneralAlarm> = preferences.all.keys.mapNotNull { it.toIntOrNull() }.sorted().mapNotNull(::load)

    fun load(id: Int): GeneralAlarm? {
        val values = preferences.getString(id.toString(), null)?.split("|") ?: return null
        if (values.size != 8) return null
        return runCatching {
            GeneralAlarm(
                id = id,
                hour = values[0].toInt().also { require(it in 0..23) },
                minute = values[1].toInt().also { require(it in 0..59) },
                repeatDays = values[2].split(",").filter { it.isNotBlank() }.map { it.toInt() }.toSet(),
                enabled = values[3].toBooleanStrict(),
                snoozeMinutes = values[4].toInt().also { require(it in 1..60) },
                vibration = values[5].toBooleanStrict(),
                soundUri = values[6].ifBlank { null }
            )
        }.getOrNull()
    }

    fun save(alarm: GeneralAlarm) {
        require(alarm.hour in 0..23 && alarm.minute in 0..59)
        require(alarm.repeatDays.all { it in 1..7 } && alarm.snoozeMinutes in 1..60)
        preferences.edit().putString(alarm.id.toString(), listOf(
            alarm.hour, alarm.minute, alarm.repeatDays.sorted().joinToString(","),
            alarm.enabled, alarm.snoozeMinutes, alarm.vibration, alarm.soundUri ?: "", ""
        ).joinToString("|")).apply()
    }

    fun delete(id: Int) = preferences.edit().remove(id.toString()).apply()
}
