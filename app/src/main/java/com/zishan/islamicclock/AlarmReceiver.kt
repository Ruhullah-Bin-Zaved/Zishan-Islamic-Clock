package com.zishan.islamicclock

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.os.Build

class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val prayer = intent.getStringExtra("prayer") ?: return
        if (intent.getStringExtra("alarmType") == "prayer") {
            PrayerRescheduler(context).reschedule(LocalDateProvider.today())
        }
        val launch = Intent(context, RingingActivity::class.java)
            .putExtra("prayer", prayer)
            .putExtra("alarmType", "prayer")
            .putExtra("alarmId", intent.getIntExtra("alarmId", -1))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        val pending = PendingIntent.getActivity(
            context, prayer.hashCode(), launch,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val manager = context.getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel("prayer_alarm", "Prayer alarms", NotificationManager.IMPORTANCE_HIGH).apply {
                    description = "Direct prayer alarm playback"
                    setSound(null, null)
                }
            )
        }
        val notification = Notification.Builder(context, "prayer_alarm")
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setContentTitle("$prayer alarm")
            .setContentText("Tap to open the ringing screen")
            .setCategory(Notification.CATEGORY_ALARM)
            .setPriority(Notification.PRIORITY_MAX)
            .setOngoing(true)
            .setAutoCancel(true)
            .setFullScreenIntent(pending, true)
            .setContentIntent(pending)
            .build()
        manager.notify(prayer.hashCode(), notification)
    }
}
