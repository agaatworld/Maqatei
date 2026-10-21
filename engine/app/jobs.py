"""Background queue. Jobs are saved in the database, so they survive closing the browser,
closing the app or restarting the device — they continue from where they stopped."""
import json
import shutil
import threading
import time
import traceback
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import db, export, media, transcribe
from .i18n import M
from .media import Cancelled

CATEGORY = {"info": "info", "fetch": "dl", "clip": "dl", "convert": "dl", "project": "dl", "transcribe": "tx"}
CHUNK = 300          # transcribe in pieces of about 5 minutes; finished pieces are kept, so work resumes
REACH = 25           # a piece ends at the pause nearest its 5-minute mark, looking this far either side
OVERLAP = 4          # only when no pause was found: seconds shared by neighbours so no word is lost
WORKERS = 4          # pieces whose audio is prepared at the same time
_running = {}        # job id -> cancel Event
_lock = threading.Lock()
_wake = threading.Event()   # set when a task is added or resumed: the loop starts it at once


# ---------- queue API ----------
def add(kind, item_id, title, bookmark_id=None, **params):
    _wake.set()
    return db.run("INSERT INTO jobs (kind, item_id, bookmark_id, title, params, status, progress, "
                  "message, created, updated) VALUES (?,?,?,?,?,'queued',0,?,?,?)",
                  (kind, item_id, bookmark_id, title, json.dumps(params), M("waiting"), db.now(), db.now()))


def set_job(jid, **kw):
    if kw.get("status") == "queued":
        _wake.set()
    kw["updated"] = db.now()
    cols = ", ".join(f"{k}=?" for k in kw)
    db.run(f"UPDATE jobs SET {cols} WHERE id=?", (*kw.values(), jid))


def pause(jid):
    set_job(jid, status="paused", message=M("paused"))
    _stop(jid)


def resume(jid):
    set_job(jid, status="queued", message=M("waiting"))


def cancel(jid):
    set_job(jid, status="cancelled", message=M("cancelled"))
    _stop(jid)
    shutil.rmtree(db.WORK / f"job{jid}", ignore_errors=True)


def _stop(jid):
    with _lock:
        ev = _running.get(jid)
    if ev:
        ev.set()


def stop_all():
    with _lock:
        for ev in _running.values():
            ev.set()


# ---------- worker loop ----------
def start():
    db.run("UPDATE jobs SET status='queued', message=? WHERE status='running'", (M("restart"),))
    threading.Thread(target=_loop, daemon=True).start()


def _loop():
    while True:
        try:
            _tick()
        except Exception:
            traceback.print_exc()
        # with work: look again soon. Without: rest (saves battery) until a new task wakes the loop.
        busy = bool(_running) or db.one("SELECT 1 FROM jobs WHERE status='queued'")
        _wake.wait(0.7 if busy else 30)
        _wake.clear()


def _tick():
    s = db.get_settings()
    limits = {"info": 4, "dl": int(s["max_downloads"]), "tx": int(s["max_transcribes"])}
    with _lock:
        busy = {}
        for jid in _running:
            j = db.one("SELECT kind FROM jobs WHERE id=?", (jid,))
            if j:
                c = CATEGORY.get(j["kind"], "dl")
                busy[c] = busy.get(c, 0) + 1
    for j in db.q("SELECT * FROM jobs WHERE status='queued' ORDER BY id"):
        with _lock:
            if j["id"] in _running:
                continue                  # previous run is still stopping
        c = CATEGORY.get(j["kind"], "dl")
        if busy.get(c, 0) >= limits[c]:
            continue
        if j["kind"] != "project":
            item = db.one("SELECT * FROM items WHERE id=?", (j["item_id"],))
            if not item:
                set_job(j["id"], status="error", message=M("item_deleted"))
                continue
            if j["kind"] != "info" and not item["dir"]:
                continue                  # still reading the link's title
        busy[c] = busy.get(c, 0) + 1
        ev = threading.Event()
        with _lock:
            _running[j["id"]] = ev
        set_job(j["id"], status="running", message=M("starting"))
        threading.Thread(target=_run, args=(j, ev), daemon=True).start()


# ---------- time: how long a task will take (learned from earlier tasks) and how long it took ----------
def _speeds():
    r = db.one("SELECT value FROM settings WHERE key='speeds'")
    try:
        return json.loads(r["value"]) if r else {}
    except Exception:
        return {}


def _learn(key, sec_per_media_sec):
    sp = _speeds()
    old = sp.get(key)
    sp[key] = sec_per_media_sec if old is None else round(0.65 * old + 0.35 * sec_per_media_sec, 5)
    db.run("INSERT OR REPLACE INTO settings (key, value) VALUES ('speeds', ?)", (json.dumps(sp),))


def measure(job, p):
    """(media seconds this task covers, the key its speed is learned under)"""
    k = job["kind"]
    if k == "project":
        clips = db.q("SELECT start, end FROM project_clips WHERE project_id=?", (p.get("project_id"),))
        return sum(max(0, (c["end"] or 0) - (c["start"] or 0)) for c in clips), "project"
    item = item_of(job)
    if not item or k == "info":
        return 0, None
    local = "local" if local_source(item) else "net"
    dur = item["duration"] or 0
    if k == "fetch":
        return dur, f"fetch_{p.get('want', 'audio')}"
    if k == "convert":
        return dur, "convert"
    a = float(p.get("start") or 0)
    b = float(p["end"]) if p.get("end") else dur
    if k == "clip":
        fk = p.get("fmt", "mp3")
        if fk != "mp3":          # instant copy and re-encoding run at very different speeds: learn them apart
            fk += "_enc" if db.get_settings().get("reencode_video") else "_copy"
        return max(0, b - a), f"clip_{fk}_{local}"
    if k == "transcribe":
        return max(0, b - a), f"tx_{db.get_settings().get('engine', 'groq')}_{local}"
    return 0, None


def timing(j, speeds=None, now=None):
    """Add eta (seconds left), est (expected total), spent and taken to a job row."""
    now = now or time.time()
    speeds = speeds if speeds is not None else _speeds()
    spent = (j.get("elapsed") or 0) + ((now - j["run_start"]) if j.get("run_start") and j.get("status") == "running" else 0)
    learned = speeds.get(j.get("speed_key") or "")
    media = j.get("media") or 0
    est_l = learned * media if learned and media else None
    p = j.get("progress") or 0
    est_p = spent / p if p > 0.03 and spent > 2 else None
    if est_p and est_l:
        w = min(1.0, p * 2.5)                  # trust the live speed more as the task advances
        est = w * est_p + (1 - w) * est_l
    else:
        est = est_p or est_l
    j["spent"] = round(spent, 1)
    j["est"] = round(est, 1) if est else None
    j["eta"] = round(max(1.0, est - spent), 1) if est and j.get("status") in ("running", "queued", "paused") else None
    return j


def _run(job, ev):
    jid = job["id"]
    last = [0.0]
    t0 = time.time()
    try:
        media, key = measure(job, json.loads(job["params"] or "{}"))
    except Exception:
        media, key = 0, None
    set_job(jid, run_start=t0, media=media, speed_key=key)

    def progress(p, msg=None):
        if ev.is_set():
            raise Cancelled()
        if p is None:                          # message only (e.g. "connection lost, retrying")
            if msg:
                set_job(jid, message=msg)
            return
        if time.time() - last[0] > 0.5 or p >= 1:
            last[0] = time.time()
            kw = {"progress": round(max(0.0, min(1.0, p)), 4)}
            if msg:
                kw["message"] = msg
            set_job(jid, **kw)

    try:
        params = json.loads(job["params"] or "{}")
        result = RUNNERS[job["kind"]](job, params, ev, progress)
        cur = db.one("SELECT status, elapsed FROM jobs WHERE id=?", (jid,))
        if cur and cur["status"] == "running":
            taken = (cur["elapsed"] or 0) + (time.time() - t0)
            set_job(jid, status="done", progress=1, message=M("done"), result=result or "", taken=round(taken, 1))
            if key and media > 5 and taken > 0.5:
                _learn(key, taken / media)
    except Cancelled:
        pass                               # paused or cancelled: status already set
    except Exception as e:
        cur = db.one("SELECT status FROM jobs WHERE id=?", (jid,))
        if cur and cur["status"] == "running":
            traceback.print_exc()
            set_job(jid, status="error", message=str(e)[:400])
    finally:
        cur = db.one("SELECT elapsed FROM jobs WHERE id=?", (jid,))
        if cur is not None:
            set_job(jid, elapsed=round((cur["elapsed"] or 0) + (time.time() - t0), 1), run_start=None)
        with _lock:
            _running.pop(jid, None)


# ---------- helpers ----------
def item_of(job):
    return db.one("SELECT * FROM items WHERE id=?", (job["item_id"],))


def lib(rel_path):
    return db.LIBRARY / rel_path


def rel(path):
    return Path(path).resolve().relative_to(db.LIBRARY.resolve()).as_posix()


def ensure_dir(item):
    if item["dir"]:
        d = lib(item["dir"])
    else:
        d = media.unique(db.LIBRARY / media.safe_name(item["title"]))
        db.run("UPDATE items SET dir=? WHERE id=?", (d.name, item["id"]))
    d.mkdir(parents=True, exist_ok=True)
    return d


def local_source(item):
    if item and item["file"] and lib(item["file"]).exists():
        return lib(item["file"])
    return None


def work(jid, fresh=False):
    d = db.WORK / f"job{jid}"
    if fresh:
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    return d


def pct(x):
    return int(x * 100)


def part_label(start, end):
    return M("range", a=media.short_time(start), b=media.short_time(end) if end else M("to_end"))


def cut_part(item, start, end, fmt, dst_noext, ev, progress, workdir, q=None):
    """Make one part as MP3 or video. From the local file if we have it, otherwise download only that part.
    q = the chosen quality: a picture height for video (1080, 720…) or a bitrate for MP3 (128, 96…)."""
    src = local_source(item)
    s = db.get_settings()
    q = int(q) if q else None
    abr = q if fmt == "mp3" else None
    height = q if fmt != "mp3" else None
    # a higher picture than the downloaded file is only on the site: cut it from there
    if src and height and item["url"] and fmt != "mp3" and height > (media.video_height(src) or 0):
        src = None
    if src:
        if fmt != "mp3" and item["media"] != "video":
            fmt = "mp3"
        exact = bool(s.get("reencode_video", False))
        ext = ".mp3" if fmt == "mp3" else ".mp4"      # MP4 keeps the exact start/end marks
        tmp = workdir / ("cut" + ext)          # finished files only appear when complete
        progress(0, M("cutting"))
        media.cut(src, tmp, start, end, fmt, ev, lambda x: progress(x, M("cutting_pct", p=pct(x))), exact=exact,
                  height=height, abr=abr)
        dst = media.unique(dst_noext.with_name(dst_noext.name + ext))
        shutil.move(str(tmp), dst)
        return dst
    # fastest: read only these minutes straight from the site (no full download, no re-reading the link)
    end_ = end or item["duration"] or None
    if end_:
        try:
            progress(0, M("dl_part"))
            inputs, _ = media.stream_urls(item["url"], "audio" if fmt == "mp3" else "video", height or s["video_height"])
            ext = ".mp3" if fmt == "mp3" else ".mp4"
            tmp = workdir / ("fast" + ext)
            media.section_from_stream(inputs, start, end_ - start, tmp, "mp3" if fmt == "mp3" else "video", ev,
                                      lambda x: progress(x, M("cutting_pct", p=pct(x))), exact=bool(s.get("reencode_video", False)), abr=abr)
            dst = media.unique(dst_noext.with_name(dst_noext.name + ext))
            shutil.move(str(tmp), dst)
            return dst
        except Cancelled:
            raise
        except Exception:
            traceback.print_exc()
            media.forget_streams(item["url"])          # fall back to the slower, surest way
    for old in workdir.glob("part.*"):
        old.unlink(missing_ok=True)
    progress(0, M("dl_part"))
    got = media.ytdlp_download(item["url"], workdir / "part.%(ext)s", "audio" if fmt == "mp3" else "video",
                               height or s["video_height"], ev, lambda x: progress(x * 0.8, M("dl_part")), section=(start, end))
    if fmt == "mp3":
        tmp = workdir / "cut.mp3"
        progress(0.85, M("making_mp3"))
        media.ffmpeg(["-i", str(got), "-map", "0:a:0", "-vn", *media.mp3_quality(abr), str(tmp)], ev)
        got.unlink(missing_ok=True)
        dst = media.unique(dst_noext.with_name(dst_noext.name + ".mp3"))
        shutil.move(str(tmp), dst)
    else:
        dst = media.unique(dst_noext.with_name(dst_noext.name + got.suffix))
        shutil.move(str(got), dst)
    return dst


# ---------- runners ----------
def run_info(job, p, ev, progress):
    item = item_of(job)
    progress(0.1, M("reading_link"))
    info = media.link_info(item["url"])
    kind = "youtube" if "youtube" in info["site"] else ("soundcloud" if "soundcloud" in info["site"] else "link")
    # keep a title the user already changed
    title = info["title"] if item["title"] == item["url"] else item["title"]
    db.run("UPDATE items SET title=?, duration=?, thumb=?, media=?, kind=?, heights=? WHERE id=?",
           (title, info["duration"], info["thumb"], info["media"], kind, json.dumps(info.get("heights") or []), item["id"]))
    item = item_of(job)
    ensure_dir(item)
    set_job(job["id"], title=M("t_read_link", t=title))
    # download the file first, so playing, cutting and transcribing all work from the phone itself
    mode = p.get("mode") or db.get_settings().get("auto_download", "video")
    if not item["file"]:
        if mode == "video" and info["media"] == "video":
            q = int(p.get("q") or 0)
            add("fetch", item["id"], M("t_dl_video", t=title) + (f" · {q}p" if q > 0 else ""), want="video",
                **({"height": q} if q else {}))
        elif mode != "none" or item["kind"] != "youtube":
            add("fetch", item["id"], M("t_dl_audio", t=title), want="audio")
    return ""


def run_fetch(job, p, ev, progress):
    item = item_of(job)
    d = ensure_dir(item)
    want = p.get("want", "audio")
    s = db.get_settings()
    progress(0, M("downloading"))
    tmpl = d / f"{media.safe_name(item['title'])} [{'video' if want != 'audio' else 'audio'}].%(ext)s"
    out = media.ytdlp_download(item["url"], tmpl, want, p.get("height") or s["video_height"], ev,
                               lambda x: progress(x * 0.98, M("downloading_pct", p=pct(x))))
    dur, kind = media.probe(out)
    adopt(item_of(job), out, dur, kind)
    return rel(out)


def adopt(cur, path, dur, kind):
    """Use a downloaded file as the item's player source — but never replace a video with audio only."""
    if kind != "video":
        if cur["kind"] == "youtube" and cur["media"] == "video":
            return
        if local_source(cur) and cur["media"] == "video":
            return
    db.run("UPDATE items SET file=?, media=?, duration=COALESCE(NULLIF(duration,0),?) WHERE id=?",
           (rel(path), kind, dur, cur["id"]))


def run_clip(job, p, ev, progress):
    item = item_of(job)
    d = ensure_dir(item) / M("parts_dir")
    d.mkdir(exist_ok=True)
    start, end, fmt = float(p["start"]), p.get("end"), p.get("fmt", "mp3")
    end = float(end) if end else None
    name = media.safe_name(p.get("name") or "")
    label = part_label(start, end)
    q = int(p.get("q") or 0)
    if q:                                      # the chosen quality is part of the name: 240p, 64k
        label += f" · {q}p" if fmt != "mp3" and q < 9999 else (f" · {q}k" if fmt == "mp3" else "")
    base = f"{name} ({label})" if name != "untitled" else label
    dst = cut_part(item, start, end, fmt, d / base, ev, progress, work(job["id"], fresh=True), p.get("q"))
    shutil.rmtree(db.WORK / f"job{job['id']}", ignore_errors=True)
    return rel(dst)


def run_convert(job, p, ev, progress):
    item = item_of(job)
    src = local_source(item)
    if not src:
        raise RuntimeError(M("need_download"))
    dst = media.unique(src.with_name(src.stem + ".mp3"))
    media.to_mp3(src, dst, ev, lambda x: progress(x, M("converting_pct", p=pct(x))), item["duration"] or None)
    return rel(dst)


def run_project(job, p, ev, progress):
    """Cut every clip of a topic project into one folder (numbered, named) and pack a ZIP with a Word book."""
    pr = db.one("SELECT * FROM projects WHERE id=?", (p["project_id"],))
    if not pr:
        raise RuntimeError(M("item_deleted"))
    clips = export.project_clips(pr["id"])
    w = work(job["id"])
    out = db.LIBRARY / M("proj_dir") / media.safe_name(pr["name"])
    if not (w / "started").exists():               # a new export starts clean; a resumed one keeps finished clips
        shutil.rmtree(out, ignore_errors=True)
        (w / "started").write_text("1")
    out.mkdir(parents=True, exist_ok=True)
    fmt = p.get("fmt", "mp3")
    n = len(clips)
    for i, c in enumerate(clips, 1):
        item = db.one("SELECT * FROM items WHERE id=?", (c["item_id"],))
        if not item:
            continue
        base = f"{i:02d} - {media.safe_name(c['title'] or item['title'], 70)}"
        dest = out / media.safe_name(c["section"], 60) if c.get("section") else out   # sub-folders of the project
        dest.mkdir(parents=True, exist_ok=True)
        if any(x.stem == base for x in dest.iterdir()):
            continue
        progress((i - 1) / (n + 1), M("exporting", d=i, n=n))
        cut_part(item, c["start"], c["end"], fmt, dest / base, ev,
                 lambda x, m=None: progress((i - 1 + x) / (n + 1), M("exporting", d=i, n=n)), w)
    progress(n / (n + 1), M("zipping"))
    book = export.build("project", pr["id"])
    opts = {"title": pr["name"], "ts": True, "notes": False, "accent": db.get_settings().get("accent")}
    (out / (media.safe_name(pr["name"]) + ".docx")).write_bytes(export.render_docx(book, opts))
    (out / (media.safe_name(pr["name"]) + ".txt")).write_text(export.render_txt(book, opts), encoding="utf-8")
    zpath = out.parent / (out.name + ".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:     # media is already compressed
        for f in sorted(out.rglob("*")):
            if f.is_file():
                z.write(f, f"{out.name}/{f.relative_to(out).as_posix()}")
    shutil.rmtree(w, ignore_errors=True)
    return rel(zpath)


def run_transcribe(job, p, ev, progress):
    """Split the audio into pieces and transcribe several at once. For online links each piece is
    read straight from the site (only those minutes), so nothing waits for a full download.
    Pieces overlap by a few seconds so no word is cut at a border. Finished pieces are kept (resume)."""
    item = item_of(job)
    s = db.get_settings()
    w = work(job["id"])
    A = float(p.get("start") or 0)
    E = float(p["end"]) if p.get("end") else None
    src, offset, remote = local_source(item), 0.0, None

    def download_source():
        nonlocal src, offset
        if E is None and A == 0:
            progress(0, M("getting_audio"))
            got = media.ytdlp_download(item["url"], ensure_dir(item) / f"{media.safe_name(item['title'])} [audio].%(ext)s",
                                       "audio", 0, ev, lambda x: progress(x * 0.15, M("getting_audio")))
            dur, kind = media.probe(got)
            adopt(item_of(job), got, dur, kind)
            src, offset = got, 0.0
        else:
            mark = w / "source.ok"
            if mark.exists() and Path(mark.read_text(encoding="utf-8")).exists():
                src = Path(mark.read_text(encoding="utf-8"))
            else:
                for old in w.glob("source.*"):
                    old.unlink(missing_ok=True)
                progress(0, M("getting_part_audio"))
                src = media.ytdlp_download(item["url"], w / "source.%(ext)s", "audio", 0, ev,
                                           lambda x: progress(x * 0.15, M("getting_part_audio")), section=(A, E))
                mark.write_text(str(src), encoding="utf-8")
            offset = A

    total = None
    if not src:
        try:
            progress(0.01, M("reading_link"))
            remote, dur = media.stream_urls(item["url"], "speech")
            total = dur or item["duration"] or None
            if not total:
                raise RuntimeError("unknown length")
        except Cancelled:
            raise
        except Exception:
            traceback.print_exc()
            remote = None
            download_source()
    if src:
        total = offset + media.probe(src)[0]
    B = min(E, total) if E else total
    if not B or B <= A:
        raise RuntimeError(M("no_length"))
    bounds = plan_pieces(w, A, B, src, offset, remote, ev, lambda: set_job(job["id"], message=M("reading_link")))
    n = len(bounds)
    done = [sum(1 for i in range(n) if (w / f"piece{i:04d}.json").exists())]
    engine = transcribe.local if s["engine"] == "local" else transcribe.groq

    def audio(i):
        """Prepare piece i's speech file (lossless, mono 16 kHz)."""
        a, b, ov = bounds[i]
        ca, cb = (max(A, a - OVERLAP) if ov[0] else a), (min(B, b + OVERLAP) if ov[1] else b)
        f = w / f"piece{i:04d}{media.SPEECH_EXT}"
        if (w / f"piece{i:04d}.json").exists() or ev.is_set():
            return f, ca
        if not (w / f"piece{i:04d}.ready").exists():
            if remote and not src:
                media.section_from_stream(remote, ca, cb - ca, f, "speech", ev)
            else:
                media.speech_chunk(src, f, ca - offset, cb - ca, ev)
            (w / f"piece{i:04d}.ready").write_text("1")
        return f, ca

    def piece(i, f, ca, context):
        """Transcribe piece i in order, with the real end of the previous piece as context."""
        out = w / f"piece{i:04d}.json"
        if out.exists():
            return json.loads(out.read_text(encoding="utf-8"))
        a, b, ov = bounds[i]
        note = lambda m: set_job(job["id"], message=M("pieces_note", m=m, d=done[0], n=n))
        r = engine(f, s, ev, note, context=context)
        keep = []
        for seg in r["segments"]:
            seg["start"] += ca
            seg["end"] += ca
            for wd in seg.get("words") or []:
                wd["s"] = round(wd["s"] + ca, 3)
                wd["e"] = round(wd["e"] + ca, 3)
            # with an overlap, each sentence belongs to the piece where it starts
            if (not ov[0] or seg["start"] >= a - 0.05) and (not ov[1] or seg["start"] < b):
                keep.append(seg)
        r = {"segments": keep, "text": " ".join(x["text"] for x in keep)}
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        tmp.replace(out)
        f.unlink(missing_ok=True)
        (w / f"piece{i:04d}.ready").unlink(missing_ok=True)
        return r

    def run_all():
        base = 0.15 if (src and offset) or (src and not local_source(item)) else 0.0
        progress(base + (1 - base) * done[0] / n, M("transcribing", d=done[0], n=n))
        context = ""
        # audio for the next pieces is prepared in the background while the current one is transcribed
        with ThreadPoolExecutor(WORKERS) as pool:
            futs = [pool.submit(audio, i) for i in range(n)]
            try:
                for i in range(n):
                    if ev.is_set():
                        raise Cancelled()
                    if (w / f"piece{i:04d}.json").exists():
                        context = json.loads((w / f"piece{i:04d}.json").read_text(encoding="utf-8"))["text"]
                        continue
                    f, ca = futs[i].result()
                    context = piece(i, f, ca, context)["text"]
                    done[0] += 1
                    progress(base + (1 - base) * done[0] / n, M("transcribing", d=done[0], n=n))
            except BaseException:
                for x in futs:
                    x.cancel()
                raise

    try:
        run_all()
    except Cancelled:
        raise
    except Exception:
        if not remote or src:
            raise
        traceback.print_exc()                      # reading straight from the site failed: download instead
        media.forget_streams(item["url"])
        remote = None
        download_source()
        run_all()
    segs, texts = [], []
    for i in range(n):
        r = json.loads((w / f"piece{i:04d}.json").read_text(encoding="utf-8"))
        segs += r["segments"]
        texts.append(r["text"])
    return save_transcript(job, item, p, segs, "\n".join(t for t in texts if t), A, E or B, s)


def plan_pieces(w, A, B, src, offset, remote, ev, note=None):
    """Split [A, B] into pieces of about CHUNK seconds that end in a pause, so no word is cut in half.
    Returns [(start, end, (overlap_before, overlap_after))]; saved, so a resumed job uses the same pieces."""
    f = w / "pieces.json"
    if f.exists():
        try:
            return [(a, b, tuple(o)) for a, b, o in json.loads(f.read_text(encoding="utf-8"))]
        except (ValueError, TypeError):
            pass
    if note:
        note()
    cuts = []
    t = A
    while B - t > CHUNK * 1.25:
        want = t + CHUNK
        lo, hi = max(t + 30, want - REACH), min(B - 5, want + REACH)
        cut = None
        try:
            if src:          # a local file starts at `offset` seconds of the lesson
                pauses = [(a + offset, b + offset) for a, b in media.silences(lo - offset, hi - lo, src=src, cancel=ev)]
            else:
                pauses = media.silences(lo, hi - lo, remote=remote, cancel=ev)
            cut = media.best_cut(want, pauses, REACH)
        except Cancelled:
            raise
        except Exception:
            traceback.print_exc()
        cuts.append((cut if cut is not None else want, cut is None))
        t = cuts[-1][0]
    pts = [(A, False)] + cuts + [(B, False)]
    out = [(round(pts[k][0], 3), round(pts[k + 1][0], 3), (pts[k][1], pts[k + 1][1])) for k in range(len(pts) - 1)]
    f.write_text(json.dumps(out), encoding="utf-8")
    return out


def save_transcript(job, item, p, segs, text, start, end, s):
    d = ensure_dir(item_of(job)) / M("tr_dir")
    d.mkdir(exist_ok=True)
    name = media.safe_name(p.get("name") or "")
    whole = not job["bookmark_id"] and start == 0 and not p.get("end")
    label = part_label(start, end)
    base = M("full_transcript") if whole else (f"{name} ({label})" if name != "untitled" else label)
    txt = media.unique(d / f"{base}.txt")
    tid = db.run("INSERT INTO transcripts (item_id, bookmark_id, title, start, end, text, segments, engine, file, created) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (item["id"], job["bookmark_id"], txt.stem, start, end, text, json.dumps(segs, ensure_ascii=False),
                  s["engine"] if s["engine"] == "local" else s["groq_model"], rel(txt), db.now()))
    write_files(db.one("SELECT * FROM transcripts WHERE id=?", (tid,)))
    shutil.rmtree(db.WORK / f"job{job['id']}", ignore_errors=True)
    return rel(txt)


def write_files(t):
    """(Re)write the .txt (with times) and .srt (subtitles) files of a transcript."""
    segs = json.loads(t["segments"] or "[]")
    txt = lib(t["file"])
    txt.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"[{media.hms(x['start'])[:8]}] {x['text']}" for x in segs] or [t["text"] or ""]
    txt.write_text("\n".join(lines), encoding="utf-8")
    st = t["start"] or 0
    txt.with_suffix(".srt").write_text("\n\n".join(
        f"{i}\n{media.hms(x['start'] - st, ',')} --> {media.hms(x['end'] - st, ',')}\n{x['text']}"
        for i, x in enumerate(segs, 1)), encoding="utf-8")


RUNNERS = {"info": run_info, "fetch": run_fetch, "clip": run_clip, "convert": run_convert,
           "transcribe": run_transcribe, "project": run_project}
