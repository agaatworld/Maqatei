"""ffmpeg and yt-dlp helpers. Every long command can be stopped via a cancel event."""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path


# tools installed next to Python (deno, yt-dlp) must be findable even if the venv isn't "activated"
os.environ["PATH"] = os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", "")

# Inside the Android app every tool is bundled and its exact place is given by the app.
APK = os.environ.get("MAQATI_APK") == "1"
PYTHON = os.environ.get("MAQATI_PYTHON") or sys.executable
YTDLP = os.environ.get("MAQATI_YTDLP")          # the yt-dlp program file (a zip Python runs directly)
QJS = os.environ.get("MAQATI_QJS")              # QuickJS, the JavaScript helper YouTube needs
YTDLP_EXE = os.environ.get("MAQATI_YTDLP_EXE")  # the desktop app: a stand-alone yt-dlp program
DENO = os.environ.get("MAQATI_DENO")            # the desktop app: Deno, the JavaScript helper YouTube needs


def M(key, **kw):
    from .i18n import M as _M        # late import: i18n needs the database
    return _M(key, **kw)


class Cancelled(Exception):
    pass


# ---------- ffmpeg ----------
def ffmpeg_path():
    p = os.environ.get("MAQATI_FFMPEG") or shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


FFMPEG = ffmpeg_path()
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0   # no black popups on Windows
UTF8_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}  # Arabic names on Windows


class Stalled(RuntimeError):
    """The command printed nothing for too long (a dead connection that never errors out)."""


def run_proc(cmd, cancel=None, on_line=None, stall=None):
    """Run a command, stream its output lines to on_line, kill it if cancel is set.
    stall = seconds of total silence after which the command is killed and Stalled is raised."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                         errors="replace", creationflags=NO_WINDOW, env=UTF8_ENV)
    stop = threading.Event()
    last = [time.monotonic()]
    stalled = [False]

    def watch():
        while not stop.wait(0.3):
            if cancel is not None and cancel.is_set():
                p.kill()
                return
            if stall and time.monotonic() - last[0] > stall:
                stalled[0] = True
                p.kill()
                return
    threading.Thread(target=watch, daemon=True).start()
    tail = []
    try:
        for line in p.stdout:
            last[0] = time.monotonic()
            line = line.rstrip()
            if not line:
                continue
            tail = (tail + [line])[-15:]
            if on_line:
                on_line(line)
        p.wait()
    except BaseException:
        p.kill()
        raise
    finally:
        stop.set()
    if cancel is not None and cancel.is_set():
        raise Cancelled()
    if stalled[0]:
        raise Stalled("stalled")
    if p.returncode != 0:
        msg = next((l for l in reversed(tail) if "ERROR" in l or "rror" in l), tail[-1] if tail else "failed")
        raise RuntimeError(msg[-300:])
    return tail


def probe(path):
    """Duration (seconds) and whether the file has real video."""
    out = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True,
                         text=True, encoding="utf-8", errors="replace",
                         creationflags=NO_WINDOW).stderr
    dur = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", out)
    if m:
        dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    video = any("Video:" in l and "attached pic" not in l for l in out.splitlines())
    return dur, ("video" if video else "audio")


def video_height(path):
    """Height in pixels of a file's video (0 when unknown or audio only)."""
    out = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW).stderr
    for l in out.splitlines():
        if "Video:" in l and "attached pic" not in l:
            s = re.search(r",\s*(\d{2,5})x(\d{2,5})", l)
            if s:
                return int(s[2])
    return 0


def ffmpeg(args, cancel=None, total=None, progress=None):
    """Run ffmpeg with a progress callback (0..1) when total seconds are known."""
    def on_line(line):
        if progress and total and line.startswith("out_time_us="):
            try:
                progress(min(1.0, int(line.split("=")[1]) / 1e6 / total))
            except ValueError:
                pass
    run_proc([FFMPEG, "-hide_banner", "-y", "-nostats", "-progress", "pipe:1", *args],
             cancel, on_line)


# video parts are copied (instant) into MP4 with an "edit list": the file carries the few frames from the
# keyframe before your start, and players start and stop exactly at your times. Re-encoding is optional.
X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k"]


def trim_edit_end(path, length):
    """Make the MP4's edit lists end exactly at `length` seconds (stream copy can run a few frames long)."""
    import struct
    try:
        d = bytearray(Path(path).read_bytes())
        i = d.find(b"mvhd")
        if i < 0:
            return
        v = d[i + 4]
        ts = struct.unpack(">I", d[i + 16:i + 20] if v == 0 else d[i + 24:i + 28])[0]
        want = int(round(length * ts))
        i, changed = 0, False
        while True:
            i = d.find(b"elst", i + 1)
            if i < 0:
                break
            v, n = d[i + 4], struct.unpack(">I", d[i + 8:i + 12])[0]
            fmt, size = (">I", 4) if v == 0 else (">Q", 8)
            for k in range(n):
                o = i + 12 + k * (size * 2 + 4)
                dur = struct.unpack(fmt, d[o:o + size])[0]
                mt = struct.unpack(">i" if v == 0 else ">q", d[o + size:o + size * 2])[0]
                if mt >= 0 and dur > want:
                    d[o:o + size] = struct.pack(fmt, want)
                    changed = True
        if changed:
            Path(path).write_bytes(bytes(d))
    except Exception:
        traceback.print_exc()


def _vbr_mp3(p):
    """True for variable-bitrate MP3 (its seek table is only approximate). Constant-bitrate ones seek exactly."""
    try:
        with open(p, "rb") as f:
            head = f.read(200000)
        return b"Xing" in head or b"VBRI" in head
    except OSError:
        return True


def mp3_quality(abr):
    """MP3 encoder settings: best (VBR ~190 kbps) or a fixed bitrate like 128."""
    return ["-c:a", "libmp3lame", "-b:a", f"{int(abr)}k"] if abr else ["-c:a", "libmp3lame", "-q:a", "2"]


def cut(src, dst, start, end, fmt, cancel=None, progress=None, exact=False, height=None, abr=None):
    """Cut [start, end] from a local file, accurate to a hundredth of a second.
    MP3 sources are decoded from the beginning (their seek index is only approximate);
    other files seek straight to the spot, then drop samples/frames up to the exact time."""
    total = (end - start) if end else None
    dur = ["-t", f"{end - start:.3f}"] if end else []
    if src.suffix.lower() == ".mp3" and _vbr_mp3(src):   # VBR mp3: only decoding from the start is exact
        head = ["-i", str(src), "-ss", f"{start:.3f}", *dur]
    else:
        head = ["-ss", f"{start:.3f}", "-i", str(src), *dur]
    if fmt == "mp3":
        args = [*head, "-map", "0:a:0", "-vn", *mp3_quality(abr), str(dst)]
        return ffmpeg(args, cancel, total, progress)
    if height and 0 < int(height) < (video_height(src) or 99999):      # a smaller picture than the original
        return ffmpeg([*head, "-map", "0:v:0?", "-map", "0:a?", "-vf", f"scale=-2:{int(height)}", *X264,
                       "-movflags", "+faststart", str(dst)], cancel, total, progress)
    if exact:
        try:
            return ffmpeg([*head, "-map", "0:v:0?", "-map", "0:a?", *X264, "-movflags", "+faststart", str(dst)],
                          cancel, total, progress)
        except Exception:
            if cancel is not None and cancel.is_set():
                raise
    args = ["-ss", f"{start:.3f}", "-i", str(src), *dur, "-map", "0:v:0?", "-map", "0:a?", "-c", "copy",
            "-movflags", "+faststart", str(dst)]
    ffmpeg(args, cancel, total, progress)
    if end:
        trim_edit_end(dst, end - start)


def to_mp3(src, dst, cancel=None, progress=None, total=None):
    ffmpeg(["-i", str(src), "-map", "0:a:0", "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(dst)],
           cancel, total, progress)


# Speech for recognition: mono 16 kHz FLAC. Lossless (an mp3 throws away detail the recogniser needs)
# and still small: about 1 MB a minute, far under the 25 MB upload limit for a 5-minute piece.
SPEECH = ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac", "-sample_fmt", "s16"]
SPEECH_EXT = ".flac"


def speech_chunk(src, dst, start, length, cancel=None):
    """One piece of speech for transcription (see SPEECH)."""
    ffmpeg(["-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(src), "-map", "0:a:0", *SPEECH, str(dst)], cancel)


NET = ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_on_network_error", "1",
       "-reconnect_delay_max", "5", "-rw_timeout", "30000000"]


def silences(start, length, src=None, remote=None, cancel=None, noise="-32dB", min_len=0.35):
    """Pauses in [start, start+length] as absolute (from, to) seconds. Reads a local file, or only these
    seconds from the site. Used to cut transcription pieces where nobody is speaking, never inside a word."""
    if src:
        inp = ["-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(src)]
    else:
        u, hdr, _ = ([i for i in remote if i[2] in ("a", "av")][:1] or remote[:1])[0]
        inp = NET + (["-headers", hdr] if hdr else []) + ["-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", u]
    out = []
    a = None

    def line(l):
        nonlocal a
        m = re.search(r"silence_start:\s*(-?[\d.]+)", l)
        if m:
            a = max(0.0, float(m[1]))
        m = re.search(r"silence_end:\s*([\d.]+)", l)
        if m and a is not None:
            out.append((start + a, start + float(m[1])))
            a = None
    run_proc([FFMPEG, "-hide_banner", "-nostats", *inp, "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000",
              "-af", f"silencedetect=noise={noise}:d={min_len}", "-f", "null", "-"], cancel, line, stall=120)
    if a is not None:
        out.append((start + a, start + length))
    return out


def best_cut(near, pauses, reach):
    """The middle of the pause closest to `near` (longer pauses win ties). None when there is no pause."""
    best, score = None, None
    for a, b in pauses:
        mid = (a + b) / 2
        if abs(mid - near) > reach:
            continue
        sc = abs(mid - near) - 4 * min(b - a, 2.0)
        if score is None or sc < score:
            best, score = mid, sc
    return best


# ---------- yt-dlp ----------
# YouTube needs a JavaScript runtime: Deno on PC (installed by pip), Node.js on Android (Termux)
JS_RUNTIME = "quickjs" if QJS else ("deno" if DENO or shutil.which("deno") else ("node" if shutil.which("node") else None))


# When YouTube says "Sign in to confirm you're not a bot", other YouTube apps' ways in often still work.
ALTS = [[], ["--extractor-args", "youtube:player_client=tv_simply,tv,web_safari"],
        ["--extractor-args", "youtube:player_client=mweb,android_vr,ios"]]
# a computer: the cookies of a browser where the user is signed in to YouTube open the door too
if not APK and os.environ.get("MAQATI_WEB") != "1":
    ALTS += [["--cookies-from-browser", b] for b in (("firefox", "edge", "chrome") if sys.platform == "win32" else ("firefox", "chrome", "safari", "edge"))]
_BLOCK = ("not a bot", "confirm you", "sign in to confirm", "--cookies", "po token", "po_token", "http error 403",
          "http error 429", "requested format is not available", "unable to extract", "precondition")


def cookies_file():
    from . import db
    p = db.DATA / "cookies.txt"
    return p if p.exists() and p.stat().st_size > 50 else None


def is_block(msg):
    m = (msg or "").lower()
    return any(w in m for w in _BLOCK)


def is_youtube(url):
    return bool(re.search(r"(youtube\.com|youtu\.be)/", url or ""))


def yt_id(url):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([\w-]{11})", url or "")
    return m.group(1) if m else None


def blocked_message(reason=""):
    """What to tell the user when every way into YouTube failed (with yt-dlp's own last words, for diagnosis)."""
    msg = M("yt_blocked" if APK else "yt_blocked_pc")
    reason = re.sub(r"^\S*ERROR:\s*", "", (reason or "").strip().splitlines()[-1] if (reason or "").strip() else "")
    return msg + (f"\n({reason[:160]})" if reason else "")


def ytdlp_base(alt=0):
    cmd = ([YTDLP_EXE] if YTDLP_EXE else [PYTHON, YTDLP] if YTDLP else [sys.executable, "-m", "yt_dlp"]) + ["--encoding", "utf-8", "--no-playlist", "--newline", "--no-colors",
           "--no-mtime", "--retries", "10", "--fragment-retries", "10",
           "--http-chunk-size", "10M"]          # asked in 10 MB pieces: YouTube does not slow these down
    if FFMPEG:
        cmd += ["--ffmpeg-location", FFMPEG]
    if JS_RUNTIME == "node":
        cmd += ["--js-runtimes", "node"]
    elif JS_RUNTIME == "deno" and DENO:
        cmd += ["--js-runtimes", f"deno:{DENO}"]
    elif JS_RUNTIME == "quickjs":
        cmd += ["--js-runtimes", f"quickjs:{QJS}"]
    ck = cookies_file()
    if ck:
        cmd += ["--cookies", str(ck)]
    return cmd + ALTS[alt]


_exe_ver = {"t": 0.0, "v": None}


def ytdlp_version():
    """The version of the yt-dlp in use (read from the file, so an update shows at once)."""
    if YTDLP_EXE:                                # a stand-alone program takes seconds to start: ask it once an hour
        if time.time() - _exe_ver["t"] < 3600:
            return _exe_ver["v"]
        try:
            out = subprocess.run([YTDLP_EXE, "--version"], capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW)
            v = (out.stdout.strip().splitlines() or [None])[0]
        except Exception:
            v = None
        _exe_ver.update(t=time.time(), v=v)
        return v
    if YTDLP:
        try:
            import zipfile
            with zipfile.ZipFile(YTDLP) as z:
                m = re.search(r"__version__\s*=\s*'([^']+)'", z.read("yt_dlp/version.py").decode("utf-8"))
                return m.group(1) if m else None
        except Exception:
            return None
    try:
        from yt_dlp.version import __version__
        return __version__
    except Exception:
        return None


YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"


def update_ytdlp(state=None):
    """Android app: use the newest yt-dlp release (YouTube changes often).
    The new file is checked before it is used, so a bad download never breaks downloads."""
    global YTDLP
    import urllib.request
    import zipfile
    state = state if state is not None else {}
    if state.get("running"):
        return False
    state.update(running=True, msg="Updating…")
    if YTDLP_EXE:                                  # the desktop app: yt-dlp updates itself
        try:
            old = ytdlp_version()
            out = subprocess.run([YTDLP_EXE, "-U"], capture_output=True, text=True, timeout=300, creationflags=NO_WINDOW)
            if out.returncode != 0:
                raise RuntimeError((out.stderr or out.stdout)[-200:])
            new = ytdlp_version()
            state.update(running=False, msg=f"yt-dlp {new}" + ("" if new != old else " ✓"), checked=time.time())
            return True
        except Exception as e:
            state.update(running=False, msg=f"Update failed: {e}"[:220])
            return False
    if not YTDLP:
        state.update(running=False, msg="")
        return False
    # The new version goes into a NEW file. A download that is running keeps reading its own file: Python reads a
    # zip program piece by piece, so replacing the file under it broke it ("bad local file header").
    from . import db
    d = db.DATA / "ytdlp"
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f"yt-dlp-{int(time.time())}.part"
    try:
        old = ytdlp_version()
        with urllib.request.urlopen(YTDLP_URL, timeout=60) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 16)
        with zipfile.ZipFile(tmp) as z:
            if "yt_dlp/version.py" not in z.namelist():
                raise RuntimeError("not yt-dlp")
        test = subprocess.run([PYTHON, str(tmp), "--version"], capture_output=True, text=True, timeout=60, env=UTF8_ENV)
        if test.returncode != 0:
            raise RuntimeError(test.stderr[-200:])
        new_file = tmp.with_suffix(".zip")
        os.replace(tmp, new_file)
        YTDLP = str(new_file)
        (d / "current").write_text(YTDLP, encoding="utf-8")
        for f in d.glob("yt-dlp-*.zip"):                # older copies: only once nothing can still be using them
            if f != new_file and time.time() - f.stat().st_mtime > 12 * 3600:
                f.unlink(missing_ok=True)
        new = ytdlp_version()
        state.update(running=False, msg=f"yt-dlp {new}" + ("" if new != old else " ✓"), checked=time.time())
        return True
    except Exception as e:
        tmp.unlink(missing_ok=True)
        state.update(running=False, msg=f"Update failed: {e}"[:220])
        return False


def use_updated_ytdlp():
    """At start: use the newest yt-dlp downloaded earlier (the bundled one stays untouched)."""
    global YTDLP
    if not YTDLP:
        return
    from . import db
    try:
        cur = (db.DATA / "ytdlp" / "current").read_text(encoding="utf-8").strip()
        if cur and Path(cur).is_file() and Path(cur).stat().st_size > 1_000_000:
            YTDLP = cur
    except OSError:
        pass


def auto_update_ytdlp(state):
    """Check for a newer yt-dlp once a day in the background (and shortly after the app starts)."""
    from . import db
    mark = db.DATA / "ytdlp-checked"

    def loop():
        time.sleep(20)
        while True:
            try:
                last = float(mark.read_text()) if mark.exists() else 0
            except (OSError, ValueError):
                last = 0
            if time.time() - last > 20 * 3600 and update_ytdlp(state):
                mark.write_text(str(time.time()))
            time.sleep(3600)
    threading.Thread(target=loop, daemon=True).start()


def _json(url, extra, timeout=150):
    """yt-dlp -J with the fallbacks above. Returns the parsed info or raises."""
    err = ""
    for alt in range(len(ALTS) if is_youtube(url) else 1):
        out = subprocess.run(ytdlp_base(alt) + ["-J"] + extra + [url], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=timeout, creationflags=NO_WINDOW, env=UTF8_ENV)
        if out.returncode == 0:
            return json.loads(out.stdout)
        lines = [l for l in out.stderr.splitlines() if "ERROR" in l]
        err = (lines[-1] if lines else out.stderr[-300:]) or "could not read link"
        if not is_block(err):
            break
    raise RuntimeError(err)


def link_heights(url, timeout=25):
    """The picture sizes a link offers, asked once and quickly (the quality menu must not wait on a blocked site)."""
    try:
        out = subprocess.run(ytdlp_base(0) + ["-J", "--skip-download", url], capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=timeout, creationflags=NO_WINDOW, env=UTF8_ENV)
        if out.returncode != 0:
            return None
        j = json.loads(out.stdout)
        return sorted({int(f["height"]) for f in j.get("formats") or [] if f.get("height") and f.get("vcodec") not in (None, "none")}, reverse=True)
    except Exception:
        return None


_infos = {}                     # link -> (time, yt-dlp's full answer with every format): asked once, reused


def link_json(url):
    """yt-dlp's full answer for a link, cached for 2 hours (its stream addresses stay valid for about 6)."""
    hit = _infos.get(url)
    if hit and time.time() - hit[0] < 2 * 3600:
        return hit[1]
    j = _json(url, ["--skip-download"])
    _infos[url] = (time.time(), j)
    return j


def link_info(url):
    try:
        j = link_json(url)
    except RuntimeError as e:
        if not (is_youtube(url) and is_block(str(e))):
            raise
        from . import mirrors
        m = mirrors.lookup(yt_id(url))
        if not m:
            raise RuntimeError(blocked_message(str(e)))
        return {"title": m["title"] or url, "duration": m["duration"], "thumb": m["thumb"], "site": "youtube",
                "id": yt_id(url), "media": "video" if m["video"] else "audio", "heights": []}
    has_video = (j.get("vcodec") not in (None, "none")) or any(
        f.get("vcodec") not in (None, "none") for f in j.get("formats") or [])
    heights = sorted({int(f["height"]) for f in j.get("formats") or [] if f.get("height")
                      and f.get("vcodec") not in (None, "none")}, reverse=True)
    return {
        "title": j.get("title") or url,
        "duration": j.get("duration") or 0,
        "thumb": j.get("thumbnail") or "",
        "site": (j.get("extractor_key") or "").lower(),
        "id": j.get("id"),
        "media": "video" if has_video else "audio",
        "heights": heights,
    }


def fmt_selector(want, height):
    if want == "audio":
        return "ba[ext=m4a]/ba/b"
    h = int(height if height is not None else 720)
    if h <= 0 or h >= 9999:                     # 0 = the original: the best picture the site has
        return "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b"
    return (f"bv*[height<={h}][ext=mp4]+ba[ext=m4a]/b[height<={h}][ext=mp4]/"
            f"bv*[height<={h}]+ba/b[height<={h}]/b")


def ytdlp_download(url, out_template, want, height, cancel=None, progress=None, section=None):
    """Download a link (or just a section of it) and return the final file path.
    yt-dlp always works in the app's own folder with a short plain name (phone shared storage and
    long Arabic names break its renames); the finished file is then moved to its real place."""
    import hashlib
    from . import db
    target = Path(out_template)
    tmpdir = db.WORK / ("dl-" + hashlib.md5(str(target).encode("utf-8")).hexdigest()[:12])
    tmpdir.mkdir(parents=True, exist_ok=True)
    got = _ytdlp(url, tmpdir / "dl.%(ext)s", want, height, cancel, progress, section)
    final = Path(str(target).replace("%(ext)s", got.suffix.lstrip(".")))
    if final.resolve() != got.resolve():
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.exists():
            final = unique(final)
        shutil.move(str(got), str(final))
    shutil.rmtree(tmpdir, ignore_errors=True)
    return final


def _ytdlp(url, out_template, want, height, cancel=None, progress=None, section=None):
    cmd = ytdlp_base() + ["-f", fmt_selector(want, height), "-o", str(out_template), "-c",
                          "-N", "4", "--progress", "--print", "after_move:filepath",
                          "--progress-template",
                          "download:PROG %(progress.downloaded_bytes)s %(progress.total_bytes)s "
                          "%(progress.total_bytes_estimate)s"]
    if want != "audio":
        cmd += ["--merge-output-format", "mp4"]
    if section:
        s, e = section
        cmd += ["--download-sections", f"*{s:.3f}-{e:.3f}" if e else f"*{s:.3f}-inf"]
    final = []
    # a video usually comes as two downloads (picture, then sound) and a join: one bar from 0 to 100% for all of it.
    # (--print keeps yt-dlp quiet, so a new download is recognised by its new total size)
    share = (0.82, 0.13) if want != "audio" else (0.97,)
    st = {"tot": None, "part": -1, "best": 0.0}

    def on_line(line):
        if line.startswith("PROG "):
            parts = line.split()[1:]
            try:
                done = float(parts[0])
                tot = next((float(x) for x in parts[1:] if x not in ("NA", "None")), 0)
                if not tot:
                    return
                if st["tot"] is None or abs(tot - st["tot"]) > max(1.0, 0.2 * st["tot"]) and done < 0.5 * tot:
                    st["part"] = min(st["part"] + 1, len(share) - 1)
                st["tot"] = tot
                i = max(0, st["part"])
                x = min(0.97, sum(share[:i]) + share[i] * min(1.0, done / tot))
                if progress and x > st["best"]:
                    st["best"] = x
                    progress(x)
            except (ValueError, IndexError):
                pass
        elif not line.startswith("[") and Path(line).suffix and Path(line).exists():
            final.append(line)
    err = None
    for alt in range(len(ALTS) if is_youtube(url) else 1):
        final.clear()
        try:
            full = cmd[:len(ytdlp_base())] and ytdlp_base(alt) + cmd[len(ytdlp_base()):] + [url]
            # A connection that silently dies (Wi-Fi <-> mobile switch, phone sleeping) makes yt-dlp wait forever.
            # Kill it after 2 quiet minutes and start again: "-c" continues from the part already downloaded.
            for attempt in range(8):
                try:
                    run_proc(full, cancel, on_line, stall=None if section else 120)
                    break
                except Stalled:
                    if attempt == 7:
                        raise RuntimeError(M("dl_stalled"))
                    if progress:
                        progress(None, M("dl_retrying"))
                    time.sleep(2)
            err = None
            break
        except RuntimeError as e:
            err = e
            if not is_block(str(e)):
                raise
    if err is not None:                                  # YouTube blocked every way in: try the free mirrors
        return _mirror_download(url, out_template, want, height, cancel, progress, section, str(err))
    if not final:   # fallback: look for the newest finished file with the expected name
        t = Path(out_template)
        stem = t.name.split(".%(ext)s")[0]
        cands = [p for p in t.parent.glob("*") if p.is_file() and p.name.startswith(stem)
                 and not p.name.endswith((".part", ".ytdl", ".tmp")) and ".part-" not in p.name]
        if cands:
            final.append(str(max(cands, key=lambda p: p.stat().st_mtime)))
    if not final:
        raise RuntimeError(M("not_found"))
    out = Path(final[-1])
    if probe(out)[0] < 0.5:
        out.unlink(missing_ok=True)
        raise RuntimeError(M("broken_file"))
    return out


# ---------- names ----------
def safe_name(s, limit=80):
    s = re.sub(r'[<>:"/\\|?*%\x00-\x1f]', " ", str(s or "")).strip()
    s = re.sub(r"\s+", " ", s).strip(" .")
    s = s[:limit]
    while len(s.encode("utf-8")) > 110:          # phones allow 255 bytes per name; stay well under
        s = s[:-1]
    return s.strip(" .") or "untitled"


def unique(path):
    path = Path(path)
    if not path.exists():
        return path
    i = 2
    while True:
        p = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not p.exists():
            return p
        i += 1


def hms(t, sep="."):
    t = max(0.0, float(t or 0))
    h, r = divmod(int(t), 3600)
    m, s = divmod(r, 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def short_time(t):
    t = int(t or 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{h}-{m:02d}-{s:02d}" if h else f"{m:02d}-{s:02d}"


# ---------- fast path: read only the needed minutes straight from the site ----------
_streams = {}
_streams_lock = threading.Lock()


def speech_selector():
    """Smallest audio that still holds full speech quality (speech is resampled to 16 kHz anyway)."""
    return "ba[abr<=80]/wa[abr>=40]/ba/b"


def pick_formats(j, want, height=720):
    """The same choice as fmt_selector / speech_selector, made from a link's full format list (no second visit)."""
    ok = [f for f in j.get("formats") or [] if f.get("url") and (f.get("protocol") or "https").split("+")[0] in
          ("https", "http", "m3u8", "m3u8_native")]
    aud = [f for f in ok if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")]
    vid = [f for f in ok if f.get("vcodec") not in (None, "none") and f.get("acodec") in (None, "none")]
    both = [f for f in ok if f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none")]
    rate = lambda f: f.get("abr") or f.get("tbr") or 0
    if want == "speech":
        small = [f for f in aud if 40 <= rate(f) <= 80]
        pick = max(small, key=rate) if small else (min([f for f in aud if rate(f) >= 40], key=rate, default=None)
                                                    or max(aud, key=rate, default=None))
        return [pick] if pick else []
    best_a = max(aud, key=lambda f: (f.get("ext") == "m4a", rate(f)), default=None)
    if want == "audio":
        return [best_a] if best_a else ([max(both, key=rate)] if both else [])
    h = int(height if height is not None else 720)
    h = 99999 if h <= 0 or h >= 9999 else h
    fit = [f for f in vid if (f.get("height") or 0) <= h]
    v = max(fit, key=lambda f: (f.get("height") or 0, f.get("ext") == "mp4", rate(f)), default=None)
    if v and best_a:
        return [v, best_a]
    fit = [f for f in both if (f.get("height") or 0) <= h]
    return [max(fit, key=lambda f: (f.get("height") or 0, rate(f)))] if fit else []


def stream_urls(url, want, height=720):
    """Direct media addresses for a link (cached for 3 hours). Returns (inputs, duration);
    inputs = [(url, headers_text, kind)] with kind 'a', 'v' or 'av'."""
    key = (url, want, int(height or 0))
    with _streams_lock:
        hit = _streams.get(key)
        if hit and time.time() - hit[0] < 3 * 3600:
            return hit[1]
    full = _infos.get(url)                  # the link was read when it was added: choose from that answer
    if full and time.time() - full[0] < 2 * 3600:
        fmts = pick_formats(full[1], want, height)
        if fmts:
            res = (_inputs(fmts), float(full[1].get("duration") or 0))
            with _streams_lock:
                _streams[key] = (time.time(), res)
            return res
    sel = speech_selector() if want == "speech" else fmt_selector(want, height)
    try:
        j = _json(url, ["-f", sel], 180)
    except RuntimeError as e:
        if not (is_youtube(url) and is_block(str(e))):
            raise
        from . import mirrors
        m = mirrors.lookup(yt_id(url))
        ins = mirrors.inputs(m, want, height) if m else []
        if not ins:
            raise RuntimeError(blocked_message(str(e)))
        res = (ins, float(m["duration"] or 0))
        with _streams_lock:
            _streams[key] = (time.time(), res)
        return res
    inputs = _inputs(j.get("requested_formats") or [j])
    if not inputs:
        raise RuntimeError("no direct stream")
    res = (inputs, float(j.get("duration") or 0))
    with _streams_lock:
        _streams[key] = (time.time(), res)
    return res


def _inputs(fmts):
    out = []
    for f in fmts:
        if not f.get("url"):
            continue
        hv = f.get("vcodec") not in (None, "none")
        ha = f.get("acodec") not in (None, "none")
        hdr = "".join(f"{k}: {v}\r\n" for k, v in (f.get("http_headers") or {}).items())
        out.append((f["url"], hdr, "av" if hv and ha else ("v" if hv else "a")))
    return out


def forget_streams(url):
    _infos.pop(url, None) if url else _infos.clear()
    with _streams_lock:
        for k in [k for k in _streams if not url or k[0] == url]:
            _streams.pop(k, None)


def section_from_stream(inputs, start, length, dst, mode, cancel=None, progress=None, exact=False, abr=None):
    """Cut [start, start+length] directly from the site with ffmpeg (only those bytes are fetched).
    mode: 'speech' (mono 16 kHz FLAC for transcription), 'mp3', or 'video'."""
    net = NET
    args = []
    use = inputs if mode == "video" else [i for i in inputs if i[2] in ("a", "av")][:1] or inputs[:1]
    if mode == "video" and not any(i[2] in ("v", "av") for i in use):
        raise RuntimeError(M("no_picture"))     # never a "video" part with sound only
    for u, hdr, _ in use:
        args += net + (["-headers", hdr] if hdr else []) + ["-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", u]
    if mode == "speech":
        args += ["-map", "0:a:0", *SPEECH]
    elif mode == "mp3":
        args += ["-map", "0:a:0", "-vn", *mp3_quality(abr)]
    else:
        if len(use) > 1:
            vi = next(i for i, x in enumerate(use) if x[2] in ("v", "av"))
            ai = next((i for i, x in enumerate(use) if x[2] in ("a", "av") and i != vi), vi)
            args += ["-map", f"{vi}:v:0", "-map", f"{ai}:a:0"]
        args += (X264 if exact else ["-c", "copy"]) + ["-movflags", "+faststart"]
    ffmpeg(args + [str(dst)], cancel, length, progress)
    if mode == "video" and not exact:
        trim_edit_end(dst, length)
    if probe(dst)[0] < 0.5:
        raise RuntimeError(M("broken_file"))


def _mirror_download(url, out_template, want, height, cancel, progress, section, reason=""):
    """Download through a free mirror (only when YouTube blocks yt-dlp)."""
    from . import mirrors
    m = mirrors.lookup(yt_id(url))
    ins = mirrors.inputs(m, "audio" if want == "audio" else "video", height) if m else []
    if not ins:
        raise RuntimeError(blocked_message(reason))
    dur = float(m["duration"] or 0)
    a, b = (section[0], section[1] or dur) if section else (0.0, dur)
    ext = "m4a" if want == "audio" else "mp4"
    dst = Path(str(out_template).replace("%(ext)s", ext))
    net = ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_on_network_error", "1", "-reconnect_delay_max", "5"]
    args = []
    for u, _, _ in ins:
        args += net + (["-ss", f"{a:.3f}"] if a else []) + (["-t", f"{b - a:.3f}"] if b and (section or a) else []) + ["-i", u]
    if want == "audio":
        args += ["-map", "0:a:0", "-vn", "-c", "copy"]
    else:
        if len(ins) > 1:
            args += ["-map", "0:v:0", "-map", "1:a:0"]
        args += ["-c", "copy", "-movflags", "+faststart"]
    ffmpeg(args + [str(dst)], cancel, (b - a) or None, progress)
    if probe(dst)[0] < 0.5:
        dst.unlink(missing_ok=True)
        raise RuntimeError(M("broken_file"))
    return dst
