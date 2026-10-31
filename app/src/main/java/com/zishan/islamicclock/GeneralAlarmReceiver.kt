package com.zishan.islamicclock

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class GeneralAlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val id = intent.getIntExtra("alarmId", -1)
        if (id < 0) return
        val store = GeneralAlarmStore(context)
        val alarm = store.load(id)
        if (alarm?.repeatDays.isNullOrEmpty()) {
            alarm?.let { store.save(it.copy(enabled = false)) }
        }
        AlarmReceiver().onReceive(
            context,
            intent.putExtra("prayer", "Alarm $id").putExtra("alarmType", "general").putExtra("alarmId", id)
        )
        GeneralAlarmScheduler(context).rescheduleAll()
    }
}
