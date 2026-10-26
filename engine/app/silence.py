"""Skipping silences, without ever touching a word.

1. The loudness of the file is measured every 20 ms (one ffmpeg pass, saved, so it is done once per file).
2. A moment is "silent" only when it is close to the file's own quiet level (its background noise), not by a fixed
   number: a lesson recorded in a mosque and one recorded at home get the right line each.
3. Only silences longer than the chosen length are taken, and a margin is always left on both sides, so the end of
   the word before and the start of the word after are kept whole. Short clicks inside a silence don't split it.

The same spans are used to jump over silences while listening and to make a copy of a file without them."""
import array
import hashlib
import math
import os
import sys

from . import db
from . import media

STEP = 0.01                       # seconds per loudness value (a hundredth of a second)
CACHE = db.DATA / "levels"
WEB = os.environ.get("MAQATI_WEB") == "1"
# how close to the background noise a moment must be to count as silence (0 = only the noise itself, 1 = speech),
# and the most silence kept around the words (half before, half after)
SENS = {"careful": (0.12, 0.4), "normal": (0.2, 0.3), "strong": (0.3, 0.2)}
KEEP_MIN = 0.06                   # even the shortest skipped silence leaves this much: the words never touch


def _key(src):
    st = src.stat()
    return hashlib.sha1(f"{src.resolve()}|{st.st_size}|{int(st.st_mtime)}|{STEP}".encode()).hexdigest()[:20]


def cached(src):
    f = CACHE / (_key(src) + ".f32")
    return f if f.exists() and f.stat().st_size else None


def measure(src, cancel=None, progress=None, total=None):
    """Loudness every 10 ms (mean power), saved next to the database. Returns the saved file."""
    f = cached(src)
    if f:
        return f
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / (_key(src) + ".f32")
    tmp = CACHE / (out.stem + ".part.f32")
    # power, averaged over about 10 ms, read every 10 ms (sharp: a silence keeps its real length)
    media.ffmpeg(["-i", str(src), "-map", "0:a:0", "-vn", "-af",
                  "aformat=channel_layouts=mono,aresample=16000,aeval=val(0)*val(0),lowpass=f=16:p=1,"
                  f"aresample={int(1 / STEP)}:filter_size=1:phase_shift=0,aeval=abs(val(0))", "-c:a", "pcm_f32le", "-f", "f32le", str(tmp)],
                 cancel, total, progress)
    os.replace(tmp, out)
    return out


def levels(f):
    a = array.array("f")
    a.frombytes(f.read_bytes())
    return [10 * math.log10(x) if x > 1e-12 else -120.0 for x in a]


def spans(lv, min_len=0.3, sens="normal"):
    """[(from, to)] seconds that can be skipped: silences of at least min_len, minus what is kept around the words.
    A long silence keeps up to the chosen margin; a short one keeps half of itself (at least KEEP_MIN), so even
    0.1-second gaps are tightened without the end of one word touching the start of the next."""
    if len(lv) < 10:
        return []
    k, keep_max = SENS.get(sens, SENS["normal"])
    s = sorted(lv)
    floor, speech = s[len(s) // 20], s[len(s) * 9 // 10]
    if speech - floor < 12:                  # no clear quiet moments (music, constant noise): skip nothing
        return []
    line = floor + (speech - floor) * k
    out, n, i = [], len(lv), 0
    while i < n:
        if lv[i] < line:
            j = i
            while j < n and lv[j] < line:
                j += 1
            ln = (j - i) * STEP
            keep = min(keep_max, max(KEEP_MIN, ln / 2))
            if ln >= min_len - 1e-6 and ln - keep >= 0.03:
                a = i * STEP + keep / 2
                out.append((round(a, 3), round(a + ln - keep, 3)))
            i = j
        else:
            i += 1
    return out


def keep_of(sp, total):
    """The parts to keep between the skipped spans."""
    keep, at = [], 0.0
    for a, b in sp:
        if a > at + 0.01:
            keep.append((at, a))
        at = b
    if total - at > 0.01:
        keep.append((at, total))
    return keep


SR, BLOCK = 48000, 240                # sound is cut in blocks of 5 ms (240 samples at 48 kHz)


def _expr(keep):
    """keep = [(first, last+1)] block numbers. A search tree on the block number n, so each block costs a few
    comparisons even with thousands of silences. (The block number, not the time: some ffmpeg versions give
    every block the same time inside this filter.)"""
    def f(lo, hi):
        if lo == hi:
            return f"gte(n,{keep[lo][0]})*lt(n,{keep[lo][1]})"
        mid = (lo + hi + 1) // 2
        return f"if(lt(n,{keep[mid][0]}),{f(lo, mid - 1)},{f(mid, hi)})"
    return f(0, len(keep) - 1) if keep else "0"


def without(src, dst, sp, total, video=False, fps=25.0, cancel=None, progress=None, abr=None):
    """Write dst: src without the spans. Sound is cut every 5 ms; with video, cuts fall on whole frames."""
    if video and fps:
        g = 1 / fps                          # same cut points for picture and sound: they stay in sync
        sp = [(math.ceil(a / g) * g, math.floor(b / g) * g) for a, b in sp]
        sp = [(a, b) for a, b in sp if b - a >= g]
    keep = keep_of(sp, total)
    blk = lambda x: int(round(x * SR / BLOCK))
    ea = _expr([(blk(a), blk(b)) for a, b in keep])
    graph = f"[0:a:0]aformat=sample_fmts=fltp,aresample={SR},asetnsamples=n={BLOCK}:p=0,aselect='{ea}',asetpts=N/SR/TB[a]"
    if video:
        fr = lambda x: int(round(x * fps))
        ev = _expr([(fr(a), fr(b)) for a, b in keep])
        graph = f"[0:v:0]fps={fps:g},select='{ev}',setpts=N/FRAME_RATE/TB[v];" + graph
    new_len = sum(b - a_ for a_, b in keep)
    script = None
    if sys.platform == "win32" and len(graph) > 20000:     # Windows limits the length of a command line
        script = dst.with_name(dst.stem + ".filter.txt")
        script.write_text(graph, encoding="utf-8")
        fc = ["-filter_complex_script", str(script)]
    else:
        fc = ["-filter_complex", graph]
    try:
        if video:
            media.ffmpeg(["-i", str(src), *fc, "-map", "[v]", "-map", "[a]", "-map_metadata", "-1", *media.X264, "-movflags", "+faststart",
                          str(dst)], cancel, new_len, progress)
        else:
            media.ffmpeg(["-i", str(src), *fc, "-map", "[a]", "-map_metadata", "-1", *media.mp3_quality(abr), str(dst)],
                         cancel, new_len, progress)
    finally:
        if script:
            script.unlink(missing_ok=True)
    got, _ = media.probe(dst)
    if new_len and abs(got - new_len) > max(1.0, new_len * 0.02):   # never hand over a file that still has them
        if video or WEB:
            raise RuntimeError(f"silences were not removed ({got:.1f}s instead of {new_len:.1f}s)")
        dst.unlink(missing_ok=True)          # this ffmpeg ignored the cut list: copy the kept sound sample by sample
        _without_wav(src, dst, keep, total, cancel, progress, abr)
    return new_len


def _without_wav(src, dst, keep, total, cancel=None, progress=None, abr=None):
    """The same result without any filter: decode to WAV, copy only the kept samples, encode. Works with every
    ffmpeg version (slower, and needs room for the decoded sound, so it is only the fallback)."""
    import wave
    full, cut = dst.with_name(dst.stem + ".full.wav"), dst.with_name(dst.stem + ".cut.wav")
    try:
        media.ffmpeg(["-i", str(src), "-map", "0:a:0", "-vn", "-ar", str(SR), "-c:a", "pcm_s16le", str(full)],
                     cancel, total, (lambda x: progress(x * 0.5)) if progress else None)
        with wave.open(str(full)) as r, wave.open(str(cut), "wb") as w:
            w.setparams(r.getparams())
            n = r.getnframes()
            for a, b in keep:
                i, j = min(n, int(round(a * SR))), min(n, int(round(b * SR)))
                r.setpos(i)
                w.writeframes(r.readframes(j - i))
        full.unlink(missing_ok=True)
        new_len = sum(b - a for a, b in keep)
        media.ffmpeg(["-i", str(cut), "-map_metadata", "-1", *media.mp3_quality(abr), str(dst)], cancel, new_len,
                     (lambda x: progress(0.5 + x * 0.5)) if progress else None)
    finally:
        full.unlink(missing_ok=True)
        cut.unlink(missing_ok=True)


def fps_of(src):
    import re
    out = media.subprocess.run([media.FFMPEG, "-hide_banner", "-i", str(src)], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", creationflags=media.NO_WINDOW).stderr
    m = re.search(r"Video:.*?(\d+(?:\.\d+)?) fps", out)
    return float(m.group(1)) if m else 25.0
