package com.zishan.islamicclock

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class SystemChangeReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == Intent.ACTION_LOCKED_BOOT_COMPLETED ||
            intent.action == Intent.ACTION_TIME_CHANGED ||
            intent.action == Intent.ACTION_TIMEZONE_CHANGED) {
            // Prayer times must be recalculated from current settings after a system change.
            PrayerRescheduler(context).reschedule(LocalDateProvider.today())
            GeneralAlarmScheduler(context).rescheduleAll()
        }
    }
}

object LocalDateProvider {
    fun today() = java.time.LocalDate.now()
}
