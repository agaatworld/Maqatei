package com.maqati.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** After the phone restarts (or the app is updated), unfinished work carries on by itself. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        val prefs = ctx.getSharedPreferences("maqati", Context.MODE_PRIVATE)
        if (prefs.getBoolean("has_work", false)) {
            try { EngineService.start(ctx) } catch (e: Exception) { /* Android may refuse; it continues when the app is opened */ }
        }
    }
}
