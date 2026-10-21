package com.maqati.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import kotlin.concurrent.thread

/**
 * Keeps the engine alive while you use Maqati and while work is running, even with the screen off or
 * another app open (a "foreground service" with a notification: Android does not kill those).
 * Shows live progress, restarts the engine if it ever stops, and stops itself when there is nothing to do.
 */
class EngineService : Service() {
    companion object {
        const val CHANNEL = "engine"
        const val NOTE_ID = 1
        const val ACTION_PAUSE_ALL = "pause_all"
        const val ACTION_QUIT = "quit"
        @Volatile var uiOpen = false          // the Maqati window is on screen
        @Volatile var playing = false         // a lesson is playing (also with the screen off): the engine serves it

        fun start(ctx: Context) {
            val i = Intent(ctx, EngineService::class.java)
            if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i) else ctx.startService(i)
        }
    }

    @Volatile private var running = false
    private var wake: PowerManager.WakeLock? = null
    private var wifi: WifiManager.WifiLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CHANNEL, "مقاطع يعمل", NotificationManager.IMPORTANCE_LOW).apply {
            description = "التحميل والقص والتفريغ في الخلفية"
            setShowBadge(false)
        })
        ServiceCompat.startForeground(this, NOTE_ID, note("مقاطع يعمل", "جاهز", null),
            if (Build.VERSION.SDK_INT >= 34) ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE else 0)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_PAUSE_ALL -> thread { Engine.post("/api/jobs-all/pause") }
            ACTION_QUIT -> { quit(); return START_NOT_STICKY }
        }
        if (!running) {
            running = true
            thread(name = "maqati-watch") { watch() }
        }
        return START_STICKY      // if Android ever stops the service, it starts it again
    }

    private fun watch() {
        var idleSince = System.currentTimeMillis()
        var failures = 0
        while (running) {
            if (!Engine.isRunning() && !Engine.healthy()) {
                if (!Engine.start(this)) failures++ else failures = 0
                if (failures > 5) {
                    update("مقاطع: تعذّر التشغيل", Engine.lastError ?: "افتح التطبيق للمحاولة مجددًا", null)
                    Thread.sleep(30_000)
                    continue
                }
            }
            val w = Engine.work()
            val busy = w != null && (w.active > 0 || w.queued > 0)
            // another device (an iPhone) may be using Maqati over the Wi-Fi: keep serving it
            val lanOn = Engine.get("/api/lan")?.contains("\"on\": true") == true
            getSharedPreferences("maqati", MODE_PRIVATE).edit().putBoolean("has_work", busy).apply()
            if (busy) {
                idleSince = System.currentTimeMillis()
                holdLocks(true)
                val pct = w!!.progress?.takeIf { !it.isNaN() }?.let { (it * 100).toInt().coerceIn(0, 100) }
                val more = if (w.active + w.queued > 1) " · ${w.active + w.queued} مهام" else ""
                update((w.title ?: "مقاطع يعمل") + more, w.message ?: "يعمل…", pct)
            } else if (lanOn) {
                idleSince = System.currentTimeMillis()
                holdLocks(true)
                update("مقاطع مفتوح للأجهزة على الواي فاي", "يمكن فتحه من الآيفون الآن. أوقفه من الإعدادات.", null)
            } else {
                holdLocks(false)
                update("مقاطع جاهز", "لا توجد مهام الآن", null)
                if (uiOpen || playing) idleSince = System.currentTimeMillis()
                // nothing to do, not on screen, nothing playing: stop after 10 minutes, to save the battery
                // (coming back within 10 minutes is instant; after that the engine starts again in a few seconds)
                if (!uiOpen && !playing && System.currentTimeMillis() - idleSince > 10 * 60_000) {
                    quit()
                    return
                }
            }
            Thread.sleep(if (busy) 2000 else if (uiOpen || playing) 5000 else 15000)
        }
    }

    /** Keep the CPU and Wi-Fi awake only while something is running. */
    private fun holdLocks(on: Boolean) {
        if (on) {
            if (wake == null) {
                wake = (getSystemService(POWER_SERVICE) as PowerManager)
                    .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "maqati:work").apply { setReferenceCounted(false); acquire(6 * 3600_000L) }
            }
            if (wifi == null) {
                @Suppress("DEPRECATION")
                wifi = (applicationContext.getSystemService(WIFI_SERVICE) as WifiManager)
                    .createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "maqati:net").apply { setReferenceCounted(false); acquire() }
            }
        } else {
            wake?.let { if (it.isHeld) it.release() }
            wake = null
            wifi?.let { if (it.isHeld) it.release() }
            wifi = null
        }
    }

    private var lastText = ""
    private fun update(title: String, text: String, pct: Int?) {
        val key = "$title|$text|$pct"
        if (key == lastText) return
        lastText = key
        getSystemService(NotificationManager::class.java).notify(NOTE_ID, note(title, text, pct))
    }

    private fun note(title: String, text: String, pct: Int?): Notification {
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP), PendingIntent.FLAG_IMMUTABLE)
        val pause = PendingIntent.getService(this, 1, Intent(this, EngineService::class.java).setAction(ACTION_PAUSE_ALL),
            PendingIntent.FLAG_IMMUTABLE)
        val quit = PendingIntent.getService(this, 2, Intent(this, EngineService::class.java).setAction(ACTION_QUIT),
            PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(open)
            .apply {
                if (pct != null) setProgress(100, pct, false)
                if (pct != null) addAction(0, "إيقاف مؤقت", pause)
            }
            .addAction(0, "إغلاق مقاطع", quit)
            .build()
    }

    private fun quit() {
        running = false
        holdLocks(false)
        Engine.stop()
        getSharedPreferences("maqati", MODE_PRIVATE).edit().putBoolean("has_work", false).apply()
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        running = false
        holdLocks(false)
        super.onDestroy()
    }
}
