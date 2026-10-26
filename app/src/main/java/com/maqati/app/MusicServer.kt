package com.maqati.app

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.util.Log
import org.json.JSONObject
import java.io.File
import java.net.InetAddress
import java.net.ServerSocket
import java.net.URLDecoder
import java.nio.FloatBuffer
import kotlin.concurrent.thread

/**
 * The engine (Python) asks the app to remove music, because only the app can run the model on a phone:
 * GET http://127.0.0.1:8776/separate?model=…&in=…&out=…&compensate=… answers when the file is written.
 * Progress goes to <out>.progress; a file <out>.stop asks it to stop. Only this phone can connect.
 */
object MusicServer {
    const val PORT = 8776
    private const val TAG = "MaqatiMusic"
    @Volatile private var started = false
    private var session: OrtSession? = null
    private var sessionPath = ""

    fun start() {
        if (started) return
        started = true
        thread(name = "maqati-music", isDaemon = true) {
            try {
                ServerSocket(PORT, 4, InetAddress.getByName("127.0.0.1")).use { srv ->
                    while (true) {
                        val s = srv.accept()
                        thread(isDaemon = true) { s.use { handle(it) } }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "server", e)
                started = false
            }
        }
    }

    private fun handle(s: java.net.Socket) {
        val line = s.getInputStream().bufferedReader().readLine() ?: return
        val path = line.split(" ").getOrNull(1) ?: return
        val q = path.substringAfter('?', "").split('&').filter { '=' in it }
            .associate { URLDecoder.decode(it.substringBefore('='), "UTF-8") to URLDecoder.decode(it.substringAfter('='), "UTF-8") }
        val res = JSONObject()
        try {
            if (!path.startsWith("/separate")) throw IllegalArgumentException("unknown")
            separate(File(q.getValue("model")), File(q.getValue("in")), File(q.getValue("out")), (q["compensate"] ?: "1").toFloat())
            res.put("ok", true)
        } catch (e: Throwable) {
            Log.e(TAG, "separate", e)
            res.put("error", e.message ?: e.toString())
        }
        val body = res.toString().toByteArray()
        s.getOutputStream().apply {
            write("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ${body.size}\r\nConnection: close\r\n\r\n".toByteArray())
            write(body); flush()
        }
    }

    private var ctx: android.content.Context? = null
    fun init(c: android.content.Context) { ctx = c.applicationContext }

    /** Phones with plenty of memory get ONNX Runtime's memory pools (about a fifth faster); others save memory. */
    private fun bigMemory(): Boolean {
        val am = ctx?.getSystemService(android.content.Context.ACTIVITY_SERVICE) as? android.app.ActivityManager ?: return false
        val mi = android.app.ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }
        return mi.totalMem >= 5_500_000_000L
    }

    private fun makeSession(env: OrtEnvironment, model: File): OrtSession {
        val opts = OrtSession.SessionOptions().apply {
            setIntraOpNumThreads(Runtime.getRuntime().availableProcessors().coerceIn(1, 4))
            if (!bigMemory()) { setCPUArenaAllocator(false); setMemoryPatternOptimization(false) }
            setExecutionMode(OrtSession.SessionOptions.ExecutionMode.SEQUENTIAL)
        }
        return env.createSession(model.path, opts)
    }

    /** One model in memory, opened once and kept (opening it again and again made a phone run out of memory). */
    @Synchronized                                   // one at a time: it uses every core of the phone
    private fun separate(model: File, inp: File, out: File, compensate: Float) {
        val env = OrtEnvironment.getEnvironment()
        if (session == null || sessionPath != model.path) {
            session?.close(); session = null
            session = makeSession(env, model)
            sessionPath = model.path
        }
        val sess = session!!
        val shape = longArrayOf(1, 4, MusicSeparator.DIM_F.toLong(), MusicSeparator.DIM_T.toLong())
        val sep = MusicSeparator { x ->
            OnnxTensor.createTensor(env, FloatBuffer.wrap(x), shape).use { t ->
                sess.run(mapOf(sess.inputNames.first() to t)).use { r ->
                    val fb = (r.get(0) as OnnxTensor).floatBuffer
                    FloatArray(fb.remaining()).also { fb.get(it) }
                }
            }
        }
        val prog = File(out.path.removeSuffix(".wav") + ".progress")
        val stop = File(out.path.removeSuffix(".wav") + ".stop")
        sep.separate(inp, out, compensate, { p -> prog.writeText(p.toString()) }, { stop.exists() })
    }
}
