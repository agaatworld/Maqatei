package com.maqati.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.widget.ProgressBar
import android.widget.Toast
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

/**
 * Updates from GitHub Releases: checks the newest release, shows what changed, downloads the APK for
 * this phone and opens Android's installer. Lessons, settings and the database stay as they are.
 */
object Updater {
    private val ui = Handler(Looper.getMainLooper())
    private const val EVERY = 3 * 3600_000L      // look for a new version at most every 3 hours, when the app opens

    fun checkOnLaunch(a: Activity) {
        val prefs = a.getSharedPreferences("maqati", Activity.MODE_PRIVATE)
        if (System.currentTimeMillis() - prefs.getLong("update_checked", 0) < EVERY) return
        prefs.edit().putLong("update_checked", System.currentTimeMillis()).apply()
        check(a, quiet = true)
    }

    private fun newer(a: String, b: String): Boolean {
        val x = a.trimStart('v').split('.', '-').map { it.toIntOrNull() ?: 0 }
        val y = b.trimStart('v').split('.', '-').map { it.toIntOrNull() ?: 0 }
        for (i in 0 until maxOf(x.size, y.size)) {
            val d = x.getOrElse(i) { 0 } - y.getOrElse(i) { 0 }
            if (d != 0) return d > 0
        }
        return false
    }

    fun check(a: Activity, quiet: Boolean) {
        if (!quiet) Toast.makeText(a, "يبحث عن تحديث…", Toast.LENGTH_SHORT).show()
        thread {
            val rel = try {
                val c = URL("https://api.github.com/repos/${BuildConfig.UPDATE_REPO}/releases/latest").openConnection() as HttpURLConnection
                c.setRequestProperty("Accept", "application/vnd.github+json")
                c.connectTimeout = 15000
                c.readTimeout = 15000
                if (c.responseCode == 200) JSONObject(c.inputStream.bufferedReader().readText()) else null
            } catch (e: Exception) { null }
            ui.post {
                if (a.isFinishing) return@post
                if (rel == null) {
                    if (!quiet) Toast.makeText(a, "تعذّر الوصول إلى GitHub. تأكد من الإنترنت.", Toast.LENGTH_LONG).show()
                    return@post
                }
                val tag = rel.optString("tag_name")
                if (!newer(tag, BuildConfig.VERSION_NAME)) {
                    if (!quiet) Toast.makeText(a, "لديك أحدث نسخة (${BuildConfig.VERSION_NAME}) ✓", Toast.LENGTH_LONG).show()
                    return@post
                }
                val abi = Build.SUPPORTED_ABIS.firstOrNull() ?: "arm64-v8a"
                val assets = rel.optJSONArray("assets")
                var url: String? = null
                for (i in 0 until (assets?.length() ?: 0)) {
                    val asset = assets!!.getJSONObject(i)
                    if (asset.optString("name").endsWith("$abi.apk")) url = asset.optString("browser_download_url")
                }
                if (url == null) {
                    if (!quiet) Toast.makeText(a, "لا توجد نسخة لهذا الهاتف ($abi)", Toast.LENGTH_LONG).show()
                    return@post
                }
                AlertDialog.Builder(a)
                    .setTitle("تحديث جديد: ${tag.trimStart('v')}")
                    .setMessage(rel.optString("body").take(1500).ifBlank { "تحسينات وإصلاحات." })
                    .setPositiveButton("تحديث الآن") { _, _ -> download(a, url!!, tag) }
                    .setNegativeButton("لاحقًا", null)
                    .show()
            }
        }
    }

    private fun download(a: Activity, url: String, tag: String) {
        val bar = ProgressBar(a, null, android.R.attr.progressBarStyleHorizontal).apply { max = 100; setPadding(48, 24, 48, 24) }
        val dlg = AlertDialog.Builder(a).setTitle("يحمّل التحديث…").setView(bar).setCancelable(false).show()
        thread {
            val dir = File(a.cacheDir, "updates").apply { mkdirs() }
            dir.listFiles()?.forEach { it.delete() }
            val out = File(dir, "maqati-$tag.apk")
            val ok = try {
                val c = URL(url).openConnection() as HttpURLConnection
                c.instanceFollowRedirects = true
                c.connectTimeout = 20000
                c.readTimeout = 60000
                val total = c.contentLengthLong
                c.inputStream.use { inp ->
                    out.outputStream().use { o ->
                        val buf = ByteArray(1 shl 16)
                        var got = 0L
                        while (true) {
                            val n = inp.read(buf)
                            if (n < 0) break
                            o.write(buf, 0, n)
                            got += n
                            if (total > 0) ui.post { bar.progress = (got * 100 / total).toInt() }
                        }
                    }
                }
                true
            } catch (e: Exception) { false }
            ui.post {
                dlg.dismiss()
                if (!ok) { Toast.makeText(a, "انقطع التحميل. حاول مجددًا.", Toast.LENGTH_LONG).show(); return@post }
                install(a, out)
            }
        }
    }

    private fun install(a: Activity, apk: File) {
        if (Build.VERSION.SDK_INT >= 26 && !a.packageManager.canRequestPackageInstalls()) {
            AlertDialog.Builder(a)
                .setTitle("خطوة واحدة")
                .setMessage("اسمح لـ«مقاطع» بتثبيت التحديثات: فعّل الخيار في الشاشة التالية، ثم ارجع واضغط «تحديث» مرة أخرى.")
                .setPositiveButton("متابعة") { _, _ ->
                    a.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${a.packageName}")))
                }
                .show()
            return
        }
        val uri = FileProvider.getUriForFile(a, "${a.packageName}.files", apk)
        a.startActivity(Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, "application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}
