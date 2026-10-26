package com.maqati.app

import android.content.Context
import android.os.Environment
import android.system.Os
import android.util.Log
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * The Maqati engine: the same Python program as on the PC, run by the Python, ffmpeg, yt-dlp and
 * QuickJS that are packed inside this APK (from the youtubedl-android library). No Termux.
 */
object Engine {
    const val PORT = 8775          // not 8765: the old Termux version may still be running there
    const val BASE = "http://127.0.0.1:$PORT"
    private const val TAG = "MaqatiEngine"

    @Volatile var process: Process? = null
        private set
    @Volatile var lastError: String? = null

    /** Unpack the tools (first start and after each app update only). Safe to call again. */
    @Synchronized
    fun prepare(ctx: Context) {
        YoutubeDL.getInstance().init(ctx)
        FFmpeg.getInstance().init(ctx)
        copyEngineIfNew(ctx)
        makeToolLinks(ctx)
    }

    private fun nativeDir(ctx: Context) = File(ctx.applicationInfo.nativeLibraryDir)
    private fun toolsBase(ctx: Context) = File(ctx.noBackupFilesDir, YoutubeDL.baseName)
    fun engineDir(ctx: Context) = File(ctx.filesDir, "engine")
    fun dataDir(ctx: Context) = File(ctx.filesDir, "data")
    fun binDir(ctx: Context) = File(ctx.filesDir, "bin")
    fun logFile(ctx: Context) = File(dataDir(ctx), "engine.log")

    /** The engine files are copied out of the APK again whenever the app was installed or updated. */
    private fun copyEngineIfNew(ctx: Context) {
        val stamp = ctx.packageManager.getPackageInfo(ctx.packageName, 0).lastUpdateTime.toString()
        val dir = engineDir(ctx)
        val mark = File(dir, ".installed")
        if (mark.exists() && mark.readText() == stamp) return
        dir.deleteRecursively()
        copyAssets(ctx, "engine", dir)
        mark.writeText(stamp)
    }

    private fun copyAssets(ctx: Context, path: String, dst: File) {
        val list = ctx.assets.list(path) ?: emptyArray()
        if (list.isEmpty()) {
            dst.parentFile?.mkdirs()
            ctx.assets.open(path).use { inp -> dst.outputStream().use { inp.copyTo(it) } }
            return
        }
        dst.mkdirs()
        for (name in list) copyAssets(ctx, "$path/$name", File(dst, name))
    }

    /** ffmpeg and ffprobe under their usual names (yt-dlp looks for both side by side). */
    private fun makeToolLinks(ctx: Context) {
        val bin = binDir(ctx)
        bin.mkdirs()
        val links = mapOf("ffmpeg" to "libffmpeg.so", "ffprobe" to "libffprobe.so", "qjs" to "libqjs.so")
        for ((name, lib) in links) {
            val link = File(bin, name)
            val target = File(nativeDir(ctx), lib).absolutePath
            try {
                val cur = try { Os.readlink(link.absolutePath) } catch (e: Exception) { null }
                if (cur != target) {
                    link.delete()
                    Os.symlink(target, link.absolutePath)
                }
            } catch (e: Exception) {
                Log.w(TAG, "symlink $name failed", e)
            }
        }
    }

    /** Where the lessons go: the phone's "Maqati" folder when allowed, else the app's own folder. */
    fun libraryDir(ctx: Context): File {
        val prefs = ctx.getSharedPreferences("maqati", Context.MODE_PRIVATE)
        prefs.getString("library", null)?.let { return File(it) }
        val shared = File(Environment.getExternalStorageDirectory(), "Maqati")
        val dir = if (Storage.hasAllFiles(ctx)) shared else File(ctx.getExternalFilesDir(null), "Maqati")
        dir.mkdirs()
        prefs.edit().putString("library", dir.absolutePath).apply()
        return dir
    }

    /** Move to the shared "Maqati" folder after the permission is given later (only if nothing is there yet). */
    fun useSharedLibraryIfAllowed(ctx: Context) {
        val prefs = ctx.getSharedPreferences("maqati", Context.MODE_PRIVATE)
        val shared = File(Environment.getExternalStorageDirectory(), "Maqati")
        val cur = prefs.getString("library", null) ?: return
        if (cur == shared.absolutePath || !Storage.hasAllFiles(ctx)) return
        val old = File(cur)
        if ((old.list()?.isNotEmpty() == true)) return     // keep the lessons where the database expects them
        shared.mkdirs()
        prefs.edit().putString("library", shared.absolutePath).apply()
    }

    private fun environment(ctx: Context): Map<String, String> {
        val base = toolsBase(ctx)
        val python = File(base, "packages/python")
        val ffmpeg = File(base, "packages/ffmpeg")
        val native = nativeDir(ctx)
        val bin = binDir(ctx)
        val ffmpegExe = File(bin, "ffmpeg").takeIf { it.exists() } ?: File(native, "libffmpeg.so")
        return mapOf(
            "LD_LIBRARY_PATH" to "${python.absolutePath}/usr/lib:${ffmpeg.absolutePath}/usr/lib",
            "SSL_CERT_FILE" to "${python.absolutePath}/usr/etc/tls/cert.pem",
            "PYTHONHOME" to "${python.absolutePath}/usr",
            "PYTHONPATH" to File(engineDir(ctx), "vendor").absolutePath,
            "PYTHONUTF8" to "1",
            "PYTHONIOENCODING" to "utf-8",
            "PYTHONUNBUFFERED" to "1",
            "HOME" to ctx.filesDir.absolutePath,
            "TMPDIR" to ctx.cacheDir.absolutePath,
            "PATH" to (System.getenv("PATH") ?: "/system/bin") + ":" + bin.absolutePath + ":" + native.absolutePath,
            "MAQATI_APK" to "1",
            "MAQATI_PYTHON" to File(native, "libpython.so").absolutePath,
            "MAQATI_YTDLP" to File(base, "${YoutubeDL.ytdlpDirName}/${YoutubeDL.ytdlpBin}").absolutePath,
            "MAQATI_QJS" to File(native, "libqjs.so").absolutePath,
            "MAQATI_FFMPEG" to ffmpegExe.absolutePath,
            "MAQATI_DATA" to dataDir(ctx).absolutePath,
            "MAQATI_LIBRARY" to libraryDir(ctx).absolutePath,
            "MAQATI_OPEN" to "0",
            "MAQATI_HOST" to "127.0.0.1",
            "MAQATI_PORT" to PORT.toString(),
            "MAQATI_MUSIC_PORT" to MusicServer.PORT.toString(),
        )
    }

    fun isRunning(): Boolean = process?.let { alive(it) } == true

    private fun alive(p: Process): Boolean = p.isAlive

    /** Start the engine if it is not running. Returns false when it could not start. */
    @Synchronized
    fun start(ctx: Context): Boolean {
        if (isRunning()) return true
        if (healthy()) return true          // an engine from before is still serving
        return try {
            prepare(ctx)
            val data = dataDir(ctx)
            data.mkdirs()
            val log = logFile(ctx)
            if (log.length() > 2_000_000) log.renameTo(File(data, "engine.old.log"))
            val pb = ProcessBuilder(File(nativeDir(ctx), "libpython.so").absolutePath, "-m", "app.main")
                .directory(engineDir(ctx))
                .redirectErrorStream(true)
                .redirectOutput(ProcessBuilder.Redirect.appendTo(log))
            pb.environment().putAll(environment(ctx))
            process = pb.start()
            lastError = null
            true
        } catch (e: Exception) {
            Log.e(TAG, "engine start failed", e)
            lastError = e.toString()
            false
        }
    }

    @Synchronized
    fun stop() {
        process?.destroy()
        process = null
    }

    fun tailLog(ctx: Context, lines: Int = 30): String = try {
        logFile(ctx).readLines().takeLast(lines).joinToString("\n")
    } catch (e: Exception) { "" }

    // ---------- talking to the engine ----------
    fun get(path: String, timeout: Int = 3000): String? = try {
        val c = URL(BASE + path).openConnection() as HttpURLConnection
        c.connectTimeout = timeout
        c.readTimeout = timeout
        try {
            if (c.responseCode in 200..299) c.inputStream.bufferedReader().readText() else null
        } finally { c.disconnect() }
    } catch (e: Exception) { null }

    fun post(path: String, json: JSONObject = JSONObject(), timeout: Int = 10000): String? = try {
        val c = URL(BASE + path).openConnection() as HttpURLConnection
        c.requestMethod = "POST"
        c.connectTimeout = timeout
        c.readTimeout = timeout
        c.doOutput = true
        c.setRequestProperty("Content-Type", "application/json")
        c.outputStream.use { it.write(json.toString().toByteArray()) }
        try {
            if (c.responseCode in 200..299) c.inputStream.bufferedReader().readText() else null
        } finally { c.disconnect() }
    } catch (e: Exception) { null }

    /** Our own engine answers (not the old Termux version, which also served Maqati on this phone). */
    fun healthy(): Boolean = get("/api/health", 1500)?.contains("\"apk\": true") == true

    data class Work(val active: Int, val queued: Int, val title: String?, val progress: Double?, val message: String?)

    /** What the engine is doing now, for the notification. */
    fun work(): Work? {
        val txt = get("/api/jobs") ?: return null
        return try {
            val arr = JSONArray(txt)
            var active = 0
            var queued = 0
            var first: JSONObject? = null
            for (i in 0 until arr.length()) {
                val j = arr.getJSONObject(i)
                when (j.optString("status")) {
                    "running" -> { active++; if (first == null) first = j }
                    "queued" -> queued++
                }
            }
            Work(active, queued, first?.optString("title"), first?.optDouble("progress"), first?.optString("message"))
        } catch (e: Exception) { null }
    }
}
