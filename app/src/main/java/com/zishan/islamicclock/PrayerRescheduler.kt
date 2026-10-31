package com.zishan.islamicclock

import android.content.Context
import java.time.LocalDate

class PrayerRescheduler(private val context: Context) {
    fun reschedule(date: LocalDate) {
        val settings = PrayerSettingsStore(context).load()
        val stored = AlarmStore(context)
        val calculator = PrayerCalculator()
        val now = java.time.ZonedDateTime.now()
        calculator.calculate(date, settings).forEach { prayer ->
            val alarm = stored.load(prayer.name)
            if (alarm?.enabled == true) {
                val calculated = prayer.adjusted
                val configured = if (alarm.manualTime) {
                    date.atTime(alarm.hour, alarm.minute).atZone(settings.zone())
                } else {
                    calculated
                }
                val target = if (configured.isAfter(now)) configured else {
                    val nextDate = date.plusDays(1)
                    val next = stored.load(prayer.name)!!
                    if (next.manualTime) nextDate.atTime(next.hour, next.minute).atZone(settings.zone())
                    else calculator.calculate(nextDate, settings).first { it.name == prayer.name }.adjusted
                }
                AlarmScheduler(context).schedule(prayer.name, target)
            } else {
                AlarmScheduler(context).cancel(prayer.name)
            }
        }
    }
}

private fun PrayerSettings.zone(): java.time.ZoneId = java.time.ZoneId.of(zoneId)
