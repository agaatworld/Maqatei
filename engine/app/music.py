"""Removing music: keeps the human voice (speech or nasheed) and removes instruments, drums and beats, with the open
UVR "MDX-Net Voc_FT" model (the owner compared two models on his own clip and chose this one).

The model (66 MB) is downloaded once, on first use. The sound is read and written in pieces of about 6 seconds that
overlap by half and are blended, so a lesson of any length needs little memory and has no seams.
Where it runs:
- PC (and the web version through the page): numpy + onnxruntime here.
- Android: the phone's Python has no numpy, so the app's own code does it (asked over a local socket, see
  MusicServer.kt); this file only prepares the sound and the model."""
import json
import os
import shutil
import time
import urllib.request
import wave

from . import db, media
from .i18n import M
from .media import Cancelled

MODEL_URL = os.environ.get("MAQATI_MUSIC_MODEL_URL",
                           "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/UVR-MDX-NET-Voc_FT.onnx")
MODEL_SIZE = 66762490
COMPENSATE = 1.021
SR = 44100
N_FFT, HOP, DIM_F, DIM_T = 7680, 1024, 3072, 256
CHUNK = HOP * (DIM_T - 1)            # 261120 samples ≈ 5.9 s
STEP = CHUNK // 2
ANDROID_PORT = os.environ.get("MAQATI_MUSIC_PORT")


def model_file():
    return db.DATA / "models" / "UVR-MDX-NET-Voc_FT.onnx"


def ensure_model(cancel=None, progress=None):
    """The model on disk (downloaded the first time; an interrupted download continues)."""
    f = model_file()
    size = MODEL_SIZE if "MAQATI_MUSIC_MODEL_URL" not in os.environ else None     # tests use a tiny stand-in model
    if f.exists() and (size is None or f.stat().st_size == size):
        return f
    f.parent.mkdir(parents=True, exist_ok=True)
    part = f.with_suffix(".part")
    import requests                          # (not urllib: on the phone only requests knows the certificates)
    for attempt in range(6):
        have = part.stat().st_size if part.exists() else 0
        try:
            if MODEL_URL.startswith("file:"):    # tests
                shutil.copy(urllib.request.url2pathname(MODEL_URL[5:]), part)
            else:
                with requests.get(MODEL_URL, headers={"Range": f"bytes={have}-"} if have else {}, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    got = have if r.status_code == 206 else 0
                    with open(part, "ab" if got else "wb") as out:
                        for b in r.iter_content(1 << 20):
                            if cancel is not None and cancel.is_set():
                                raise Cancelled()
                            out.write(b)
                            got += len(b)
                            if progress:
                                progress(got / MODEL_SIZE, M("music_model", p=min(99, int(got * 100 / MODEL_SIZE))))
            if size is None or part.stat().st_size == size:
                os.replace(part, f)
                return f
        except Cancelled:
            raise
        except Exception:
            if attempt == 5:
                raise RuntimeError(M("music_model_fail"))
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(M("music_model_fail"))


def available():
    """Can this device remove music? (PC: numpy + onnxruntime; Android: the app's own code.)"""
    if ANDROID_PORT:
        return True
    import importlib.util
    return all(importlib.util.find_spec(m) is not None for m in ("numpy", "onnxruntime"))


# ---------- the separation itself (numpy) ----------
class _Mdx:
    def __init__(self, model):
        import numpy as np
        import onnxruntime as ort
        self.np = np
        so = ort.SessionOptions()
        so.intra_op_num_threads = max(1, (os.cpu_count() or 2))
        self.sess = ort.InferenceSession(str(model), so, providers=["CPUExecutionProvider"])
        self.win = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N_FFT) / N_FFT)).astype(np.float32)
        self.idx = np.arange(DIM_T)[:, None] * HOP + np.arange(N_FFT)[None, :]
        n = N_FFT + HOP * (DIM_T - 1)
        self.norm = np.zeros(n, np.float32)
        for t in range(DIM_T):
            self.norm[t * HOP:t * HOP + N_FFT] += self.win ** 2
        self.norm = np.maximum(self.norm, 1e-8)
        self.fade = (np.hanning(CHUNK) + 1e-3).astype(np.float32)

    def run(self, chunk):
        """[2, CHUNK] mix -> [2, CHUNK] voice"""
        np = self.np
        p = np.pad(chunk, ((0, 0), (N_FFT // 2, N_FFT // 2)), mode="reflect")
        s = np.fft.rfft(p[:, self.idx] * self.win, axis=-1).transpose(0, 2, 1)[:, :DIM_F]
        x = np.stack([s.real, s.imag], 1).reshape(1, 4, DIM_F, DIM_T).astype(np.float32)
        y = self.sess.run(None, {"input": x})[0].reshape(2, 2, DIM_F, DIM_T)
        spec = np.zeros((2, N_FFT // 2 + 1, DIM_T), np.complex64)
        spec[:, :DIM_F] = y[:, 0] + 1j * y[:, 1]
        frames = np.fft.irfft(spec.transpose(0, 2, 1), n=N_FFT, axis=-1) * self.win
        out = np.zeros((2, len(self.norm)), np.float32)
        for t in range(DIM_T):
            out[:, t * HOP:t * HOP + N_FFT] += frames[:, t]
        return (out / self.norm)[:, N_FFT // 2:N_FFT // 2 + CHUNK]


def _separate_numpy(model, src_wav, dst_wav, cancel=None, progress=None):
    m = _Mdx(model)
    np = m.np
    with wave.open(str(src_wav)) as r, wave.open(str(dst_wav), "wb") as w:
        n = r.getnframes()
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)

        def read(k):
            a = np.frombuffer(r.readframes(k), np.int16).astype(np.float32) / 32768
            return a.reshape(-1, 2).T

        buf = read(CHUNK)
        acc = np.zeros((2, CHUNK + STEP), np.float32)
        wacc = np.zeros(CHUNK + STEP, np.float32)
        done, pos = 0, 0
        while pos < n:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            chunk = buf if buf.shape[1] == CHUNK else np.pad(buf, ((0, 0), (0, CHUNK - buf.shape[1])))
            acc[:, :CHUNK] += m.run(chunk) * m.fade
            wacc[:CHUNK] += m.fade
            k = min(STEP, n - done)                         # the first half is now final
            out = np.clip(acc[:, :k] / wacc[:k] * COMPENSATE, -1, 1)
            w.writeframes((out.T * 32767).astype(np.int16).tobytes())
            done += k
            acc = np.concatenate([acc[:, STEP:], np.zeros((2, STEP), np.float32)], 1)
            wacc = np.concatenate([wacc[STEP:], np.zeros(STEP, np.float32)])
            pos += STEP
            buf = np.concatenate([buf[:, STEP:], read(STEP)], 1)
            if progress:
                progress(min(1.0, done / max(1, n)))
            if done >= n:
                break


def _separate_android(model, src_wav, dst_wav, cancel=None, progress=None):
    """The app does the work; this side waits, shows its progress and can stop it."""
    import hashlib                                    # the phone closed the app while it worked: don't loop forever
    tries = db.DATA / "music-tries" / (hashlib.sha1(str(dst_wav).encode()).hexdigest()[:16] + ".txt")
    tries.parent.mkdir(parents=True, exist_ok=True)   # (kept outside the task's folder, which a restart may empty)
    n = int(tries.read_text() or 0) if tries.exists() else 0
    if n >= 2:
        tries.unlink(missing_ok=True)
        raise RuntimeError(M("music_memory"))
    tries.write_text(str(n + 1))
    prog = dst_wav.with_suffix(".progress")
    stop = dst_wav.with_suffix(".stop")
    q = urllib.request.quote
    url = f"http://127.0.0.1:{ANDROID_PORT}/separate?model={q(str(model))}&in={q(str(src_wav))}&out={q(str(dst_wav))}" \
          f"&compensate={COMPENSATE}"
    import threading
    res = {}

    def call():
        try:
            with urllib.request.urlopen(url, timeout=24 * 3600) as r:
                res["body"] = json.loads(r.read() or b"{}")
        except Exception as e:
            res["error"] = str(e)
    th = threading.Thread(target=call, daemon=True)
    th.start()
    while th.is_alive():
        if cancel is not None and cancel.is_set():
            stop.write_text("1")
            th.join(30)
            raise Cancelled()
        try:
            if progress and prog.exists():
                progress(float(prog.read_text() or 0))
        except ValueError:
            pass
        th.join(1.0)
    prog.unlink(missing_ok=True)
    stop.unlink(missing_ok=True)
    if not res.get("error"):
        tries.unlink(missing_ok=True)
    if res.get("error") or (res.get("body") or {}).get("error"):
        raise RuntimeError(res.get("error") or res["body"]["error"])


def remove_music(src, dst, video, cancel=None, progress=None, workdir=None):
    """dst: src with only the voice. Video keeps its picture untouched; only the sound changes."""
    model = ensure_model(cancel, lambda x, msg=None: progress and progress(x * 0.15, msg))
    workdir.mkdir(parents=True, exist_ok=True)
    mix, voice = workdir / "mix.wav", workdir / "voice.wav"
    total, _ = media.probe(src)
    progress and progress(0.15, M("music_prepare"))
    media.ffmpeg(["-i", str(src), "-map", "0:a:0", "-vn", "-ac", "2", "-ar", str(SR), "-c:a", "pcm_s16le", str(mix)], cancel)
    sep = _separate_android if ANDROID_PORT else _separate_numpy
    sep(model, mix, voice, cancel, lambda x: progress and progress(0.17 + x * 0.78, M("music_working", p=int(x * 100))))
    progress and progress(0.95, M("music_writing"))
    if video:
        media.ffmpeg(["-i", str(src), "-i", str(voice), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                      "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(dst)], cancel, total)
    else:
        media.ffmpeg(["-i", str(voice), "-map_metadata", "-1", "-c:a", "libmp3lame", "-b:a", "192k", str(dst)], cancel, total)
    mix.unlink(missing_ok=True)
    voice.unlink(missing_ok=True)
    return dst


def cleanup(workdir):
    shutil.rmtree(workdir, ignore_errors=True)
