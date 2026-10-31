package com.zishan.islamicclock

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import java.time.DayOfWeek
import java.time.ZoneId
import java.time.ZonedDateTime

class GeneralAlarmScheduler(private val context: Context) {
    private val manager = context.getSystemService(AlarmManager::class.java)

    fun rescheduleAll() {
        val store = GeneralAlarmStore(context)
        store.all().forEach { alarm ->
            cancel(alarm.id)
            if (!alarm.enabled) return@forEach
            val now = ZonedDateTime.now()
            val next = (0..7).asSequence().map { now.plusDays(it.toLong()).withHour(alarm.hour).withMinute(alarm.minute).withSecond(0).withNano(0) }
                .firstOrNull { it.isAfter(now) && (alarm.repeatDays.isEmpty() || it.dayOfWeek.value in alarm.repeatDays) }
            if (next != null) schedule(alarm.id, next)
        }
    }

    fun schedule(id: Int, at: ZonedDateTime) {
        val pending = pending(id, PendingIntent.FLAG_UPDATE_CURRENT)
        if (at.toInstant().toEpochMilli() <= System.currentTimeMillis()) return
        if (android.os.Build.VERSION.SDK_INT < 31 || manager.canScheduleExactAlarms()) {
            manager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at.toInstant().toEpochMilli(), pending)
        } else {
            manager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at.toInstant().toEpochMilli(), pending)
        }
    }

    fun cancel(id: Int) {
        pending(id, PendingIntent.FLAG_NO_CREATE)?.let(manager::cancel)
    }

    private fun pending(id: Int, flag: Int): PendingIntent = PendingIntent.getBroadcast(
        context, id, Intent(context, GeneralAlarmReceiver::class.java).putExtra("alarmId", id),
        flag or PendingIntent.FLAG_IMMUTABLE
    )
}
