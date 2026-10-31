package com.zishan.islamicclock

import android.app.Activity
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

private val emerald = Color.rgb(0, 200, 120)
private val ivory = Color.rgb(242, 255, 248)

fun Activity.screen(title: String): LinearLayout = LinearLayout(this).apply {
    orientation = LinearLayout.VERTICAL
    setPadding(24, 32, 24, 24)
    setBackgroundColor(Color.BLACK)
    addView(TextView(this@screen).apply {
        text = title
        textSize = 26f
        setTextColor(emerald)
        setPadding(0, 0, 0, 20)
    })
}

fun Activity.scroll(content: View): ScrollView = ScrollView(this).apply {
    setBackgroundColor(Color.BLACK)
    addView(content)
}

fun Activity.label(value: String, size: Float = 17f): TextView = TextView(this).apply {
    text = value
    textSize = size
    setTextColor(ivory)
    setPadding(0, 8, 0, 8)
}

fun Activity.action(value: String, callback: () -> Unit): Button = Button(this).apply {
    text = value
    setTextColor(ivory)
    setOnClickListener { callback() }
}

fun Activity.field(value: String, hint: String): EditText = EditText(this).apply {
    setText(value)
    this.hint = hint
    setTextColor(ivory)
    setHintTextColor(Color.GRAY)
    inputType = android.text.InputType.TYPE_CLASS_TEXT
}

class AnalogClockView(private val activity: Activity) : View(activity) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val handler = Handler(Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() { invalidate(); handler.postDelayed(this, 1000) }
    }

    override fun onAttachedToWindow() { super.onAttachedToWindow(); handler.post(tick) }
    override fun onDetachedFromWindow() { handler.removeCallbacks(tick); super.onDetachedFromWindow() }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.BLACK)
        val cx = width / 2f
        val cy = height / 2f
        val radius = min(width, height) * 0.38f
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 5f
        paint.color = emerald
        canvas.drawCircle(cx, cy, radius, paint)
        val now = LocalDateTime.now()
        val second = now.second + now.nano / 1_000_000_000f
        val minute = now.minute + second / 60f
        val hour = (now.hour % 12) + minute / 60f
        hand(canvas, cx, cy, radius * .52f, hour / 12f, 9f, ivory)
        hand(canvas, cx, cy, radius * .72f, minute / 60f, 6f, ivory)
        hand(canvas, cx, cy, radius * .82f, second / 60f, 2f, emerald)
        paint.style = Paint.Style.FILL
        paint.color = emerald
        canvas.drawCircle(cx, cy, 9f, paint)
    }

    private fun hand(canvas: Canvas, cx: Float, cy: Float, length: Float, fraction: Float, width: Float, color: Int) {
        val angle = (fraction * Math.PI * 2.0) - Math.PI / 2.0
        paint.color = color
        paint.strokeWidth = width
        canvas.drawLine(cx, cy, cx + cos(angle).toFloat() * length, cy + sin(angle).toFloat() * length, paint)
    }
}

class AnalogClockActivity : Activity() {
    private var fullScreen = false
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val root = screen("Analog clock")
        root.addView(AnalogClockView(this), LinearLayout.LayoutParams(-1, 0, 1f))
        lateinit var toggle: Button
        toggle = action("Enter full-screen clock") {
            fullScreen = !fullScreen
            window.decorView.systemUiVisibility = if (fullScreen) {
                View.SYSTEM_UI_FLAG_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            } else {
                View.SYSTEM_UI_FLAG_VISIBLE
            }
            toggle.text = if (fullScreen) "Exit full-screen clock" else "Enter full-screen clock"
        }
        root.addView(toggle)
        setContentView(root)
    }

    override fun onBackPressed() {
        if (fullScreen) {
            fullScreen = false
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_VISIBLE
        } else {
            super.onBackPressed()
        }
    }
}

class StopwatchActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private var running = false
    private var startedAt = 0L
    private var elapsed = 0L
    private lateinit var display: TextView
    private lateinit var laps: TextView
    private val update = object : Runnable {
        override fun run() { updateDisplay(); if (running) handler.postDelayed(this, 50) }
    }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val root = screen("Stopwatch")
        display = label("00:00.00", 40f)
        laps = label("")
        root.addView(display)
        root.addView(action("Start / Pause") { if (running) pause() else start() })
        root.addView(action("Lap") { if (running) laps.text = "${laps.text}\n${format(elapsedNow())}" })
        root.addView(action("Reset") { running = false; elapsed = 0; laps.text = ""; updateDisplay() })
        root.addView(laps)
        setContentView(scroll(root))
    }

    private fun start() { startedAt = System.currentTimeMillis() - elapsed; running = true; handler.post(update) }
    private fun pause() { elapsed = elapsedNow(); running = false }
    private fun elapsedNow() = if (running) System.currentTimeMillis() - startedAt else elapsed
    private fun updateDisplay() { display.text = format(elapsedNow()) }
    private fun format(value: Long) = "%02d:%02d.%02d".format(value / 60000, (value / 1000) % 60, (value / 10) % 100)
}
