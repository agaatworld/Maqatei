package com.maqati.app

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.io.RandomAccessFile
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin

/** With a model that keeps everything, the sound must come back unchanged: checks the spectrogram maths and the
 *  blending of the pieces (the same steps as the engine's music.py). */
class MusicSeparatorTest {
    @Test fun keepsTheSoundWhenTheModelKeepsEverything() {
        val sr = 44100
        val n = sr * 17 + 12345                       // several pieces and an uneven end
        val src = File.createTempFile("mix", ".wav")
        val dst = File.createTempFile("voice", ".wav")
        val sig = Array(2) { c -> FloatArray(n) { i -> (0.3 * sin(2 * PI * (220 + 110 * c) * i / sr) + 0.2 * sin(2 * PI * 3000 * i / sr) * sin(2 * PI * 0.5 * i / sr)).toFloat() } }
        RandomAccessFile(src, "rw").use { f ->
            fun le(v: Int, k: Int) = ByteArray(k) { (v shr (8 * it) and 0xff).toByte() }
            f.write("RIFF".toByteArray()); f.write(le(36 + n * 4, 4)); f.write("WAVEfmt ".toByteArray())
            f.write(le(16, 4)); f.write(le(1, 2)); f.write(le(2, 2)); f.write(le(sr, 4)); f.write(le(sr * 4, 4)); f.write(le(4, 2)); f.write(le(16, 2))
            f.write("data".toByteArray()); f.write(le(n * 4, 4))
            val b = ByteArray(n * 4)
            for (i in 0 until n) for (c in 0 until 2) { val q = (sig[c][i] * 32767).toInt(); b[(i * 2 + c) * 2] = q.toByte(); b[(i * 2 + c) * 2 + 1] = (q shr 8).toByte() }
            f.write(b)
        }
        var last = 0f
        MusicSeparator { it.copyOf() }.separate(src, dst, 1f, { last = it }, { false })
        val out = dst.readBytes()
        assertTrue("length kept", out.size == 44 + n * 4)
        var worst = 0f; var at = 0
        for (i in 0 until n - 2048) for (c in 0 until 2) {          // the last 46 ms meet the abrupt end of the test sound
            val o = (i * 2 + c) * 2 + 44
            val v = ((out[o].toInt() and 0xff) or (out[o + 1].toInt() shl 8)).toShort() / 32768f
            if (abs(v - sig[c][i]) > worst) { worst = abs(v - sig[c][i]); at = i }
        }
        println("worst difference: $worst at $at of $n (step ${MusicSeparator.STEP}), last progress $last")
        assertTrue("sound unchanged (worst $worst)", worst < 0.002f)
        assertTrue("progress reaches the end", last >= 0.999f)
    }
}
