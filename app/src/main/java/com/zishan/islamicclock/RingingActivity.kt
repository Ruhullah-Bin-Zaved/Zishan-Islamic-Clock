package com.zishan.islamicclock

import android.app.Activity
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.provider.Settings
import android.net.Uri
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

class RingingActivity : Activity() {
    private var player: MediaPlayer? = null
    private var vibrator: Vibrator? = null
    private var audioManager: AudioManager? = null
    private var audioFocusRequest: AudioFocusRequest? = null
    private var isFinishingRinging = false
    private var prayerName = "Prayer"
    private var alarmType = "prayer"
    private var generalAlarmId = -1

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val prayer = intent.getStringExtra("prayer") ?: "Prayer"
        prayerName = prayer
        alarmType = intent.getStringExtra("alarmType") ?: "prayer"
        generalAlarmId = intent.getIntExtra("alarmId", -1)
        val title = TextView(this).apply { text = prayer; textSize = 32f; gravity = Gravity.CENTER }
        val dismiss = Button(this).apply { text = "Dismiss"; setOnClickListener { finishRinging() } }
        val snooze = Button(this).apply {
            text = "Snooze"
            setOnClickListener {
                val minutes = if (alarmType == "general" && generalAlarmId >= 0) {
                    GeneralAlarmStore(this@RingingActivity).load(generalAlarmId)?.snoozeMinutes ?: 10
                } else {
                    AlarmStore(this@RingingActivity).load(prayer)?.snoozeMinutes ?: 10
                }
                if (alarmType == "general" && generalAlarmId >= 0) {
                    GeneralAlarmScheduler(this@RingingActivity).schedule(
                        generalAlarmId, java.time.ZonedDateTime.now().plusMinutes(minutes.toLong())
                    )
                } else {
                    AlarmScheduler(this@RingingActivity).schedule(
                        prayer, java.time.ZonedDateTime.now().plusMinutes(minutes.toLong())
                    )
                }
                finishRinging()
            }
        }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(32, 32, 32, 32)
            addView(title)
            addView(dismiss)
            addView(snooze)
        })
        val alarm = if (alarmType == "general" && generalAlarmId >= 0) {
            GeneralAlarmStore(this).load(generalAlarmId)
        } else {
            AlarmStore(this).load(prayer)
        }
        val soundSettings = getSharedPreferences("sound_settings", MODE_PRIVATE)
        vibrator = getSystemService(Vibrator::class.java)
        if (alarm?.vibration ?: soundSettings.getBoolean("vibration", true)) {
            vibrator?.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 500, 500), 0))
        }
        audioManager = getSystemService(AudioManager::class.java)
        audioFocusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM).build())
            .build()
        audioManager?.requestAudioFocus(audioFocusRequest!!)
        val alarmUri = alarm?.soundUri?.let(Uri::parse)
            ?: soundSettings.getString("uri", null)?.let(Uri::parse)
            ?: Settings.System.DEFAULT_ALARM_ALERT_URI
        if (alarmUri != null) {
            runCatching {
                player = MediaPlayer().apply {
                    setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM).build())
                    setDataSource(this@RingingActivity, alarmUri)
                    setOnCompletionListener { finishRinging() }
                    prepare()
                    start()
                }
            }.onFailure { player?.release(); player = null }
        }
    }

    private fun finishRinging() {
        if (isFinishingRinging) return
        isFinishingRinging = true
        vibrator?.cancel()
        audioFocusRequest?.let { audioManager?.abandonAudioFocusRequest(it) }
        player?.release()
        player = null
        getSystemService(android.app.NotificationManager::class.java).cancel(prayerName.hashCode())
        finish()
    }

    override fun onDestroy() {
        finishRinging()
        super.onDestroy()
    }
}
