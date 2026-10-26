package com.maqati.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.print.PrintAttributes
import android.print.PrintManager
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject
import java.net.URLDecoder
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {
    private lateinit var web: WebView
    private lateinit var splash: LinearLayout
    private lateinit var splashText: TextView
    private lateinit var splashRetry: Button
    private val ui = Handler(Looper.getMainLooper())
    private val prefs by lazy { getSharedPreferences("maqati", MODE_PRIVATE) }
    private var loaded = false
    private var pendingShare: String? = null
    private var pendingFile: Uri? = null
    private var fileCallback: ValueCallback<Array<Uri>>? = null

    private val pickFiles = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        val cb = fileCallback ?: return@registerForActivityResult
        fileCallback = null
        val data = res.data
        if (res.resultCode != RESULT_OK || data == null) { cb.onReceiveValue(null); return@registerForActivityResult }
        val clip = data.clipData
        val uris = if (clip != null) Array(clip.itemCount) { clip.getItemAt(it).uri } else data.data?.let { arrayOf(it) } ?: arrayOf()
        cb.onReceiveValue(uris)
    }
    private val askNotify = registerForActivityResult(ActivityResultContracts.RequestPermission()) { nextSetupStep() }
    private val askLegacyStorage = registerForActivityResult(ActivityResultContracts.RequestPermission()) { nextSetupStep() }
    private val returnFromSettings = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { nextSetupStep() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        EngineService.uiOpen = true
        buildViews()
        setupWeb()
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (web.canGoBack()) web.goBack() else moveTaskToBack(true)   // keep working in the background
            }
        })
        pendingShare = sharedLink(intent)
        pendingFile = sharedFile(intent)
        nextSetupStep()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        sharedLink(intent)?.let { pendingShare = it; if (loaded) addShared() }
        sharedFile(intent)?.let { pendingFile = it; if (loaded) addShared() }
    }

    override fun onResume() {
        super.onResume()
        EngineService.uiOpen = true
        if (::web.isInitialized) web.resumeTimers()
        if (prefs.getBoolean("setup_done", false)) {
            Engine.useSharedLibraryIfAllowed(this)
            EngineService.start(this)
            if (loaded) thread { if (!waitHealthy(15)) ui.post { showSplash(); waitAndLoad() } }
        }
    }

    /** Off screen: the page stops working (unless a lesson is playing), and the engine may rest. */
    override fun onPause() {
        super.onPause()
        EngineService.uiOpen = false
        if (::web.isInitialized && !EngineService.playing) web.pauseTimers()
    }

    override fun onDestroy() {
        EngineService.uiOpen = false
        EngineService.playing = false
        super.onDestroy()
    }

    // ---------- first run: ask once for what Maqati needs, explained in plain Arabic ----------
    private fun nextSetupStep() {
        val step = prefs.getInt("setup_step", 0)
        when {
            step <= 0 -> {
                prefs.edit().putInt("setup_step", 1).apply()
                if (Storage.hasAllFiles(this)) return nextSetupStep()
                AlertDialog.Builder(this)
                    .setTitle("مكان حفظ دروسك")
                    .setMessage("مقاطع يحفظ الدروس والمقاطع والتفريغات في مجلد «Maqati» في هاتفك، فتراها في تطبيق الملفات وتبقى حتى لو حذفت التطبيق.\n\nفي الشاشة التالية فعّل «السماح بإدارة جميع الملفات» ثم ارجع.")
                    .setCancelable(false)
                    .setPositiveButton("متابعة") { _, _ ->
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                            val i = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName"))
                            try { returnFromSettings.launch(i) } catch (e: ActivityNotFoundException) {
                                returnFromSettings.launch(Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION))
                            }
                        } else askLegacyStorage.launch(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    }
                    .setNegativeButton("لاحقًا") { _, _ -> nextSetupStep() }
                    .show()
            }
            step == 1 -> {
                prefs.edit().putInt("setup_step", 2).apply()
                if (Build.VERSION.SDK_INT >= 33 &&
                    checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                    askNotify.launch(Manifest.permission.POST_NOTIFICATIONS)
                } else nextSetupStep()
            }
            step == 2 -> {
                prefs.edit().putInt("setup_step", 3).apply()
                if (!ignoresBattery()) {
                    AlertDialog.Builder(this)
                        .setTitle("العمل في الخلفية")
                        .setMessage("حتى لا يوقف الهاتف التحميل أو التفريغ عند إغلاق الشاشة، اضغط «سماح» في الشاشة التالية.")
                        .setCancelable(false)
                        .setPositiveButton("متابعة") { _, _ -> askBackground(returnFromSettings = true) }
                        .setNegativeButton("لاحقًا") { _, _ -> nextSetupStep() }
                        .show()
                } else nextSetupStep()
            }
            else -> {
                prefs.edit().putBoolean("setup_done", true).apply()
                Engine.libraryDir(this)       // fixes the library place now that the storage answer is known
                EngineService.start(this)
                waitAndLoad()
                Updater.checkOnLaunch(this)
                offerRemoveOldApp()
            }
        }
    }

    private fun installed(pkg: String): Boolean = try { packageManager.getPackageInfo(pkg, 0); true } catch (e: Exception) { false }

    /** The old Maqati (the window that opened the Termux version) has the same name and icon: offer to remove it. */
    private fun offerRemoveOldApp() {
        if (!installed("com.maqati.app")) return
        val termux = installed("com.termux")
        AlertDialog.Builder(this)
            .setTitle("احذف «مقاطع» القديم")
            .setMessage("ما زال تطبيق «مقاطع» القديم مثبتًا، وله نفس الاسم والأيقونة، فيفتح النسخة القديمة 3.6.1.\n\nاضغط «احذف القديم» ثم «موافق». دروسك في مجلد Maqati لا تُحذف." +
                if (termux) "\n\nولم تعد تحتاج Termux: يمكنك حذفه أيضًا إن لم تستعمله لشيء آخر." else "")
            .setPositiveButton("احذف القديم") { _, _ ->
                try { startActivity(Intent(Intent.ACTION_DELETE, Uri.parse("package:com.maqati.app"))) } catch (e: Exception) { }
            }
            .setNegativeButton("لاحقًا", null)
            .show()
    }

    private fun ignoresBattery(): Boolean =
        (getSystemService(POWER_SERVICE) as PowerManager).isIgnoringBatteryOptimizations(packageName)

    @SuppressLint("BatteryLife")
    fun askBackground(returnFromSettings: Boolean = false) {
        val i = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName"))
        try {
            if (returnFromSettings) this.returnFromSettings.launch(i) else startActivity(i)
        } catch (e: ActivityNotFoundException) {
            if (returnFromSettings) nextSetupStep()
        }
    }

    // ---------- the window ----------
    private fun buildViews() {
        val root = FrameLayout(this)
        web = WebView(this)
        web.visibility = View.INVISIBLE
        root.addView(web, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        splash = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.parseColor("#F6F4EF"))
            setPadding(48, 48, 48, 48)
        }
        splash.addView(TextView(this).apply {
            text = "مقاطع"
            textSize = 34f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#2F6F62"))
            gravity = Gravity.CENTER
        })
        splash.addView(ProgressBar(this).apply { setPadding(0, 32, 0, 24) })
        splashText = TextView(this).apply {
            text = "يجهّز التطبيق…"
            textSize = 16f
            setTextColor(Color.parseColor("#555555"))
            gravity = Gravity.CENTER
        }
        splash.addView(splashText)
        splashRetry = Button(this).apply {
            text = "حاول مجددًا"
            visibility = View.GONE
            setOnClickListener { visibility = View.GONE; Engine.stop(); EngineService.start(this@MainActivity); waitAndLoad() }
        }
        splash.addView(splashRetry)
        root.addView(splash, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        setContentView(root)
    }

    private fun showSplash() {
        splash.visibility = View.VISIBLE
        splashText.text = "يجهّز التطبيق…"
    }

    private fun waitHealthy(seconds: Int): Boolean {
        repeat(seconds * 4) {
            if (Engine.healthy()) return true
            Thread.sleep(250)
        }
        return false
    }

    /** Wait for the engine (the first start unpacks the tools: up to a minute), then show Maqati. */
    private fun waitAndLoad() {
        thread {
            val first = !prefs.getBoolean("started_once", false)
            if (first) ui.post { splashText.text = "أول تشغيل: تجهيز الأدوات (دقيقة تقريبًا)…" }
            val ok = waitHealthy(if (first) 180 else 60)
            ui.post {
                if (ok) {
                    prefs.edit().putBoolean("started_once", true).apply()
                    loaded = true
                    web.loadUrl(Engine.BASE + "/")
                } else {
                    splashText.text = "تعذّر تشغيل المحرك.\n" + (Engine.lastError ?: Engine.tailLog(this, 6))
                    splashRetry.visibility = View.VISIBLE
                }
            }
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWeb() {
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess = false
            textZoom = 100
            cacheMode = WebSettings.LOAD_NO_CACHE        // never show an old copy of the app after an update
            setSupportMultipleWindows(false)
        }
        web.setBackgroundColor(Color.TRANSPARENT)
        web.addJavascriptInterface(Bridge(), "MaqatiApp")
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, req: WebResourceRequest): Boolean {
                val u = req.url
                if (u.host == "127.0.0.1" || u.host == "localhost") return false
                try { startActivity(Intent(Intent.ACTION_VIEW, u)) } catch (e: ActivityNotFoundException) { }
                return true                                   // other sites open in the phone's browser
            }

            override fun onPageFinished(view: WebView, url: String) {
                if (url.startsWith(Engine.BASE)) {
                    splash.visibility = View.GONE
                    web.visibility = View.VISIBLE
                    addShared()
                }
            }
        }
        web.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(view: WebView, cb: ValueCallback<Array<Uri>>, params: FileChooserParams): Boolean {
                fileCallback?.onReceiveValue(null)
                fileCallback = cb
                val types = params.acceptTypes.filter { it.isNotBlank() }.flatMap { it.split(",") }.map { it.trim() }
                    .map { if (it.startsWith(".")) "*/*" else it }.distinct()
                val i = Intent(Intent.ACTION_GET_CONTENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*")
                if (types.isNotEmpty() && "*/*" !in types) i.putExtra(Intent.EXTRA_MIME_TYPES, types.toTypedArray())
                if (params.mode == FileChooserParams.MODE_OPEN_MULTIPLE) i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
                return try { pickFiles.launch(i); true } catch (e: ActivityNotFoundException) { fileCallback = null; false }
            }
        }
        web.setDownloadListener { url, _, disposition, mime, _ -> saveToDownloads(url, disposition, mime) }
    }

    /** "Download" in Maqati: put a copy in the phone's Download/Maqati folder, straight away.
     *  (The system download service queues files and can wait a long time; the file is already on the phone.) */
    private fun saveToDownloads(url: String, disposition: String?, mime: String?) {
        val name0 = fileName(disposition) ?: Uri.parse(url).lastPathSegment ?: "maqati"
        Toast.makeText(this, "جارٍ الحفظ…", Toast.LENGTH_SHORT).show()
        Thread {
            try {
                val conn = (java.net.URL(url).openConnection() as java.net.HttpURLConnection).apply {
                    connectTimeout = 15000
                    readTimeout = 600000
                }
                if (conn.responseCode !in 200..299) throw java.io.IOException("HTTP ${conn.responseCode}")
                val name = fileName(conn.getHeaderField("Content-Disposition")) ?: name0
                val type = mime?.takeIf { it.isNotBlank() && it != "application/octet-stream" } ?: conn.contentType ?: "application/octet-stream"
                conn.inputStream.use { input -> writeDownload(name, type) { out -> input.copyTo(out, 1 shl 16) } }
                runOnUiThread { Toast.makeText(this, "✓ حُفظ في التنزيلات ← Maqati\n$name", Toast.LENGTH_LONG).show() }
            } catch (e: Exception) {
                runOnUiThread { Toast.makeText(this, "تعذّر الحفظ: ${e.message}", Toast.LENGTH_LONG).show() }
            }
        }.start()
    }

    /** Write a new file into Download/Maqati (MediaStore on Android 10+, the folder itself before that). */
    private fun writeDownload(name: String, mime: String, write: (java.io.OutputStream) -> Unit) {
        if (Build.VERSION.SDK_INT >= 29) {
            val v = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                put(MediaStore.MediaColumns.MIME_TYPE, mime)
                put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Maqati")
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
            val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v) ?: throw java.io.IOException("no space")
            try {
                (contentResolver.openOutputStream(uri) ?: throw java.io.IOException("cannot write")).use(write)
            } catch (e: Exception) {
                contentResolver.delete(uri, null, null)
                throw e
            }
            v.clear()
            v.put(MediaStore.MediaColumns.IS_PENDING, 0)
            contentResolver.update(uri, v, null, null)
        } else {
            @Suppress("DEPRECATION")
            val dir = java.io.File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "Maqati")
            dir.mkdirs()
            var f = java.io.File(dir, name)
            var n = 2
            while (f.exists()) { f = java.io.File(dir, name.substringBeforeLast('.') + " ($n)" + (if ('.' in name) "." + name.substringAfterLast('.') else "")); n++ }
            java.io.FileOutputStream(f).use(write)
        }
    }

    private fun fileName(disposition: String?): String? {
        if (disposition == null) return null
        Regex("filename\\*=UTF-8''([^;]+)", RegexOption.IGNORE_CASE).find(disposition)?.let {
            return URLDecoder.decode(it.groupValues[1], "UTF-8").replace("/", "_")
        }
        return Regex("filename=\"?([^\";]+)").find(disposition)?.groupValues?.get(1)
    }

    // ---------- links shared from YouTube or any other app ----------
    private fun sharedLink(i: Intent?): String? {
        if (i?.action != Intent.ACTION_SEND) return null
        val text = i.getStringExtra(Intent.EXTRA_TEXT) ?: return null
        return Regex("https?://\\S+").find(text)?.value
    }

    /** An audio or video file shared to Maqati from another app (WhatsApp, Files, the gallery…). */
    private fun sharedFile(i: Intent?): Uri? {
        if (i?.action != Intent.ACTION_SEND) return null
        val type = i.type ?: return null
        if (!type.startsWith("audio/") && !type.startsWith("video/")) return null
        @Suppress("DEPRECATION")
        return if (Build.VERSION.SDK_INT >= 33) i.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java) else i.getParcelableExtra(Intent.EXTRA_STREAM)
    }

    /** Send a shared file to the engine as a new lesson (the same as choosing it in "Add"). */
    private fun addSharedFile(uri: Uri) {
        thread {
            var name = "file"
            var size = -1L
            try {
                contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)?.use { c ->
                    if (c.moveToFirst()) { c.getString(0)?.let { name = it }; if (!c.isNull(1)) size = c.getLong(1) }
                }
            } catch (e: Exception) { }
            var tmp: java.io.File? = null
            val id = try {
                if (size < 0) {                          // size unknown: keep a copy first (the engine needs the length)
                    tmp = java.io.File(cacheDir, "shared.bin")
                    contentResolver.openInputStream(uri)!!.use { inp -> tmp.outputStream().use { inp.copyTo(it) } }
                    size = tmp.length()
                }
                val c = java.net.URL(Engine.BASE + "/api/upload?name=" + java.net.URLEncoder.encode(name, "UTF-8")).openConnection() as java.net.HttpURLConnection
                c.requestMethod = "POST"; c.doOutput = true; c.setFixedLengthStreamingMode(size)
                (tmp?.inputStream() ?: contentResolver.openInputStream(uri)!!).use { inp -> c.outputStream.use { inp.copyTo(it) } }
                JSONObject(c.inputStream.bufferedReader().readText()).getJSONArray("ids").getInt(0)
            } catch (e: Exception) { null } finally { tmp?.delete() }
            ui.post {
                Toast.makeText(this, if (id != null) "أُضيف الملف إلى المكتبة ✓" else "تعذّرت إضافة الملف", Toast.LENGTH_LONG).show()
                if (id != null) web.evaluateJavascript("location.hash='#/item/$id'", null)
            }
        }
    }

    private fun addShared() {
        pendingFile?.let { pendingFile = null; addSharedFile(it) }
        val link = pendingShare ?: return
        pendingShare = null
        thread {
            val res = Engine.post("/api/links", JSONObject().put("text", link))
            val id = try { res?.let { JSONObject(it).getJSONArray("ids").getInt(0) } } catch (e: Exception) { null }
            ui.post {
                Toast.makeText(this, if (res != null) "أُضيف الرابط إلى المكتبة ✓" else "تعذّرت إضافة الرابط", Toast.LENGTH_LONG).show()
                if (id != null) web.evaluateJavascript("location.hash='#/item/$id'", null)
            }
        }
    }

    // ---------- what the page can ask the app to do ----------
    inner class Bridge {
        @JavascriptInterface fun appVersion(): String = BuildConfig.VERSION_NAME
        @JavascriptInterface fun playing(on: Boolean) { EngineService.playing = on }
        /** Share text (a link to a moment, a title) to WhatsApp or any app. */
        @JavascriptInterface fun share(text: String) {
            ui.post {
                val i = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text)
                startActivity(Intent.createChooser(i, "مشاركة"))
            }
        }
        /** Share one of the library's files (a part, a lesson, a transcript) to any app. */
        @JavascriptInterface fun shareFile(path: String, mime: String?) {
            ui.post {
                try {
                    val f = java.io.File(Engine.libraryDir(this@MainActivity), path).canonicalFile
                    if (!f.path.startsWith(Engine.libraryDir(this@MainActivity).canonicalPath) || !f.isFile) throw IllegalArgumentException(path)
                    val uri = androidx.core.content.FileProvider.getUriForFile(this@MainActivity, "$packageName.files", f)
                    val i = Intent(Intent.ACTION_SEND).setType(mime ?: "*/*").putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    startActivity(Intent.createChooser(i, "مشاركة"))
                } catch (e: Exception) {
                    Toast.makeText(this@MainActivity, "تعذّرت مشاركة الملف", Toast.LENGTH_LONG).show()
                }
            }
        }
        @JavascriptInterface fun checkUpdate() { ui.post { Updater.check(this@MainActivity, quiet = false) } }
        @JavascriptInterface fun askBackground() { ui.post { this@MainActivity.askBackground() } }
        @JavascriptInterface fun print(title: String?) {
            ui.post {
                val pm = getSystemService(PRINT_SERVICE) as PrintManager
                val name = (title ?: "Maqati").ifBlank { "Maqati" }
                pm.print(name, web.createPrintDocumentAdapter(name), PrintAttributes.Builder().build())
            }
        }
    }
}
