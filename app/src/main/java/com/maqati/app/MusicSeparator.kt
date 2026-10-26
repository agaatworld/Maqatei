package com.maqati.app

import org.jtransforms.fft.FloatFFT_1D
import java.io.File
import java.io.RandomAccessFile
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Removing music on the phone: the same steps as the engine's music.py (UVR MDX-Net "Voc_FT"), written here because
 * the phone's Python has no numpy. Reads a 44.1 kHz stereo 16-bit WAV in pieces of about 6 s that overlap by a quarter,
 * turns each piece into a spectrogram, lets the model keep the voice, turns it back into sound and blends the pieces.
 * The model itself is behind [Model], so the sound maths can be checked without it.
 */
class MusicSeparator(private val model: Model) {
    fun interface Model { fun run(input: FloatArray): FloatArray }   // [1, 4, DIM_F, DIM_T] -> same

    companion object {
        const val N_FFT = 7680
        const val HOP = 1024
        const val DIM_F = 3072
        const val DIM_T = 256
        const val CHUNK = HOP * (DIM_T - 1)
        const val STEP = CHUNK * 3 / 4         // pieces overlap by a quarter (the UVR default)
        const val BINS = N_FFT / 2 + 1
        private const val PAD = N_FFT / 2
    }

    private val fft = FloatFFT_1D(N_FFT.toLong())
    private val win = FloatArray(N_FFT) { (0.5 - 0.5 * cos(2 * PI * it / N_FFT)).toFloat() }
    private val olaLen = N_FFT + HOP * (DIM_T - 1)
    private val norm = FloatArray(olaLen).also { n ->
        for (t in 0 until DIM_T) for (i in 0 until N_FFT) n[t * HOP + i] += win[i] * win[i]
        for (i in n.indices) n[i] = max(n[i], 1e-8f)
    }
    private val fade = FloatArray(CHUNK) { (0.5 - 0.5 * cos(2 * PI * it / (CHUNK - 1))).toFloat() + 1e-3f }

    /** One piece: [2][CHUNK] mix -> [2][CHUNK] voice. */
    fun runChunk(ch: Array<FloatArray>): Array<FloatArray> {
        val input = FloatArray(4 * DIM_F * DIM_T)
        val frame = FloatArray(N_FFT)
        for (c in 0 until 2) {
            val x = ch[c]
            for (t in 0 until DIM_T) {
                val start = t * HOP - PAD
                for (i in 0 until N_FFT) frame[i] = reflect(x, start + i) * win[i]
                fft.realForward(frame)
                // packed: frame[0]=Re0, frame[1]=Re(N/2), frame[2k]=Re k, frame[2k+1]=Im k
                for (f in 0 until DIM_F) {
                    val re = if (f == 0) frame[0] else frame[2 * f]
                    val im = if (f == 0) 0f else frame[2 * f + 1]
                    input[((c * 2) * DIM_F + f) * DIM_T + t] = re
                    input[((c * 2 + 1) * DIM_F + f) * DIM_T + t] = im
                }
            }
        }
        val y = model.run(input)
        val out = Array(2) { FloatArray(olaLen) }
        for (c in 0 until 2) {
            for (t in 0 until DIM_T) {
                java.util.Arrays.fill(frame, 0f)
                for (f in 0 until DIM_F) {
                    val re = y[((c * 2) * DIM_F + f) * DIM_T + t]
                    val im = y[((c * 2 + 1) * DIM_F + f) * DIM_T + t]
                    if (f == 0) frame[0] = re else { frame[2 * f] = re; frame[2 * f + 1] = im }
                }
                fft.realInverse(frame, true)
                val o = out[c]
                for (i in 0 until N_FFT) o[t * HOP + i] += frame[i] * win[i]
            }
        }
        return Array(2) { c -> FloatArray(CHUNK) { i -> out[c][PAD + i] / norm[PAD + i] } }
    }

    private fun reflect(x: FloatArray, i: Int): Float {
        var j = i
        val n = x.size
        if (j < 0) j = -j
        if (j >= n) j = 2 * (n - 1) - j
        return x[min(max(j, 0), n - 1)]
    }

    /**
     * src: 44.1 kHz stereo 16-bit WAV -> dst: the voice only, same format.
     * progress(0..1) is called after each piece; stop() is asked between pieces.
     */
    fun separate(src: File, dst: File, compensate: Float, progress: (Float) -> Unit, stop: () -> Boolean) {
        RandomAccessFile(src, "r").use { inp ->
            val dataStart = findData(inp)
            val n = ((inp.length() - dataStart) / 4).toInt()        // stereo frames
            inp.seek(dataStart)
            RandomAccessFile(dst, "rw").use { out ->
                out.setLength(0)
                writeHeader(out, n)
                val buf = Array(2) { FloatArray(CHUNK) }
                readInto(inp, buf, 0, CHUNK)
                val acc = Array(2) { FloatArray(CHUNK + STEP) }
                val wacc = FloatArray(CHUNK + STEP)
                var done = 0
                val bytes = ByteArray(STEP * 4)
                while (done < n) {
                    if (stop()) throw InterruptedException("stopped")
                    val v = runChunk(buf)
                    for (c in 0 until 2) for (i in 0 until CHUNK) acc[c][i] += v[c][i] * fade[i]
                    for (i in 0 until CHUNK) wacc[i] += fade[i]
                    val k = min(STEP, n - done)
                    for (i in 0 until k) for (c in 0 until 2) {
                        val s = (acc[c][i] / wacc[i] * compensate).coerceIn(-1f, 1f)
                        val q = (s * 32767f).roundToInt()
                        bytes[(i * 2 + c) * 2] = (q and 0xff).toByte()
                        bytes[(i * 2 + c) * 2 + 1] = (q shr 8 and 0xff).toByte()
                    }
                    out.write(bytes, 0, k * 4)
                    done += k
                    for (c in 0 until 2) {
                        System.arraycopy(acc[c], STEP, acc[c], 0, CHUNK)
                        java.util.Arrays.fill(acc[c], CHUNK, CHUNK + STEP, 0f)
                        System.arraycopy(buf[c], STEP, buf[c], 0, CHUNK - STEP)
                    }
                    System.arraycopy(wacc, STEP, wacc, 0, CHUNK)
                    java.util.Arrays.fill(wacc, CHUNK, CHUNK + STEP, 0f)
                    readInto(inp, buf, CHUNK - STEP, STEP)
                    progress(min(1f, done.toFloat() / max(1, n)))
                }
            }
        }
    }

    /** Fill buf[c][at until at+count] from the file; past the end: silence. */
    private fun readInto(inp: RandomAccessFile, buf: Array<FloatArray>, at: Int, count: Int) {
        val b = ByteArray(count * 4)
        var got = 0
        while (got < b.size) { val r = inp.read(b, got, b.size - got); if (r <= 0) break; got += r }
        for (i in 0 until count) for (c in 0 until 2) {
            val o = (i * 2 + c) * 2
            buf[c][at + i] = if (o + 1 < got) ((b[o].toInt() and 0xff) or (b[o + 1].toInt() shl 8)).toShort() / 32768f else 0f
        }
    }

    private fun findData(f: RandomAccessFile): Long {
        f.seek(12)
        val h = ByteArray(8)
        while (f.filePointer < f.length()) {
            f.readFully(h)
            val size = (h[4].toLong() and 0xff) or ((h[5].toLong() and 0xff) shl 8) or ((h[6].toLong() and 0xff) shl 16) or ((h[7].toLong() and 0xff) shl 24)
            if (String(h, 0, 4) == "data") return f.filePointer
            f.seek(f.filePointer + size + (size and 1))
        }
        throw IllegalArgumentException("not a WAV file")
    }

    private fun writeHeader(f: RandomAccessFile, frames: Int) {
        val data = frames * 4
        fun le(v: Int, n: Int) = ByteArray(n) { (v shr (8 * it) and 0xff).toByte() }
        f.write("RIFF".toByteArray()); f.write(le(36 + data, 4)); f.write("WAVEfmt ".toByteArray())
        f.write(le(16, 4)); f.write(le(1, 2)); f.write(le(2, 2)); f.write(le(44100, 4)); f.write(le(44100 * 4, 4))
        f.write(le(4, 2)); f.write(le(16, 2)); f.write("data".toByteArray()); f.write(le(data, 4))
    }
}
