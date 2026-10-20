package com.maqati.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.AlertDialog
import android.app.DownloadManager
import android.content.ActivityNotFoundException
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
        nextSetupStep()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        sharedLink(intent)?.let { pendingShare = it; if (loaded) addShared() }
    }

    override fun onResume() {
        super.onResume()
        EngineService.uiOpen = true
        if (prefs.getBoolean("setup_done", false)) {
            Engine.useSharedLibraryIfAllowed(this)
            EngineService.start(this)
            if (loaded) thread { if (!waitHealthy(15)) ui.post { showSplash(); waitAndLoad() } }
        }
    }

    override fun onDestroy() {
        EngineService.uiOpen = false
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
            }
        }
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

    /** "Download" in Maqati: put a copy in the phone's Download/Maqati folder. */
    private fun saveToDownloads(url: String, disposition: String?, mime: String?) {
        val name = fileName(disposition) ?: Uri.parse(url).lastPathSegment ?: "maqati"
        try {
            val req = DownloadManager.Request(Uri.parse(url))
                .setTitle(name)
                .setMimeType(mime)
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "Maqati/$name")
            (getSystemService(DOWNLOAD_SERVICE) as DownloadManager).enqueue(req)
            Toast.makeText(this, "يُحفظ في التنزيلات ← Maqati", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(this, "تعذّر الحفظ: ${e.message}", Toast.LENGTH_LONG).show()
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

    private fun addShared() {
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
