"""Maqati — web server using only Python's standard library (runs on PC and on Android/Termux).
Start with:  python -m app.main"""
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from . import db, export, jobs, lan, media, search, silence, smart, transcribe
from .i18n import M, lang as ui_lang
from .version import VERSION

STATIC = Path(__file__).parent / "static"
ANDROID = "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/system/build.prop")
APK = media.APK                                  # running inside the Maqati Android app (no Termux)
HOSTED = os.environ.get("MAQATI_HOSTED") == "1"   # running behind the multi-user gateway on a shared server
DESKTOP = os.environ.get("MAQATI_DESKTOP") == "1" # the Windows / Mac app (desktop/maqati_desktop.py)
LAST = time.time()                                # when the page last asked for something (the desktop app stops when idle)
for ext, t in {".m4a": "audio/mp4", ".mp3": "audio/mpeg", ".webm": "video/webm", ".mkv": "video/x-matroska",
               ".opus": "audio/ogg", ".srt": "text/plain", ".txt": "text/plain", ".webmanifest": "application/manifest+json",
               ".js": "text/javascript", ".css": "text/css"}.items():
    mimetypes.add_type(t, ext)


class HTTPError(Exception):
    def __init__(self, code, msg=""):
        self.code, self.msg = code, msg


class Raw:
    def __init__(self, data, ctype, download_name=None):
        self.data, self.ctype, self.download_name = data, ctype, download_name


class FileOut:
    def __init__(self, path, download=False, nocache=False):
        self.path, self.download, self.nocache = Path(path), download, nocache


ROUTES = []


def route(method, pattern):
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn
    return deco


# ---------- pages & files ----------
@route("GET", "/")
def index(r):
    """The page, with each script/style address stamped by its file time, so a phone never keeps an old copy."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for name in ("app.js", "style.css", "fonts.css", "theme.css", "icons.js", "reminders.js"):
        stamp = int((STATIC / name).stat().st_mtime)
        html = html.replace(f"/static/{name}\"", f"/static/{name}?v={stamp}\"")
    return Raw(html.encode("utf-8"), "text/html; charset=utf-8")


@route("GET", "/sw.js")
def sw(r):
    return FileOut(STATIC / "sw.js", nocache=True)


@route("GET", "/static/(?P<name>[\\w./-]+)")
def static(r, name):
    p = (STATIC / name).resolve()
    if STATIC.resolve() not in p.parents or not p.is_file():
        raise HTTPError(404)
    return FileOut(p, nocache=not name.startswith("fonts/"))


@route("GET", "/media/(?P<path>.+)")
def get_media(r, path):
    p = (db.LIBRARY / unquote(path)).resolve()
    if db.LIBRARY.resolve() not in p.parents or not p.is_file():
        raise HTTPError(404)
    return FileOut(p, download=r.query.get("dl") == "1")


# ---------- library ----------
@route("GET", "/api/state")
def state(r):
    items = db.q("SELECT i.*, (SELECT COUNT(*) FROM bookmarks b WHERE b.item_id=i.id) AS bookmarks, "
                 "(SELECT COUNT(*) FROM excerpts x WHERE x.item_id=i.id) AS excerpts, "
                 "(SELECT progress FROM jobs j WHERE j.item_id=i.id AND j.kind IN ('fetch','info') "
                 " AND j.status IN ('running','queued') ORDER BY j.id DESC LIMIT 1) AS dl_progress, "
                 "(SELECT COUNT(*) FROM transcripts t WHERE t.item_id=i.id) AS trs, "
                 "(SELECT COUNT(*) FROM notes n WHERE n.item_id=i.id) AS notes "
                 "FROM items i ORDER BY i.id DESC")
    return {"folders": db.q("SELECT * FROM folders ORDER BY name"), "items": items}


@route("POST", "/api/folders")
def new_folder(r):
    return {"id": db.run("INSERT INTO folders (name, created) VALUES (?,?)",
                         ((r.body.get("name") or "").strip() or "New folder", db.now()))}


@route("PATCH", "/api/folders/(?P<fid>\\d+)")
def rename_folder(r, fid):
    for k in ("name", "color", "icon"):
        if r.body.get(k) is not None:
            db.run(f"UPDATE folders SET {k}=? WHERE id=?", (str(r.body[k]).strip(), int(fid)))
    return {"ok": True}


@route("POST", "/api/folders/(?P<fid>\\w+)/transcribe-all")
def folder_transcribe_all(r, fid):
    """Transcribe every item in a folder that has no full transcript yet (for topic search)."""
    where = "" if fid == "all" else (" WHERE folder_id IS NULL" if fid == "none" else " WHERE folder_id=?")
    args = () if fid in ("all", "none") else (int(fid),)
    n = 0
    for i in db.q("SELECT * FROM items" + where, args):
        has = db.one("SELECT id FROM transcripts WHERE item_id=? AND bookmark_id IS NULL AND start=0", (i["id"],))
        busy = db.one("SELECT id FROM jobs WHERE item_id=? AND kind='transcribe' AND bookmark_id IS NULL "
                      "AND status IN ('queued','running','paused')", (i["id"],))
        if not has and not busy:
            jobs.add("transcribe", i["id"], M("t_tx_all", t=i["title"]))
            n += 1
    return {"queued": n}


@route("DELETE", "/api/folders/(?P<fid>\\d+)")
def del_folder(r, fid):
    db.run("UPDATE items SET folder_id=NULL WHERE folder_id=?", (int(fid),))
    db.run("DELETE FROM folders WHERE id=?", (int(fid),))
    return {"ok": True}


@route("POST", "/api/links")
def add_links(r):
    ids = []
    urls = [u for u in (r.body.get("text") or "").split() if u.startswith(("http://", "https://"))]
    name = (r.body.get("name") or "").strip()[:200]     # a name the user typed: kept instead of the site's title
    for url in urls:
        title = name if name and len(urls) == 1 else url
        iid = db.run("INSERT INTO items (folder_id, title, kind, url, media, duration, created) VALUES (?,?,?,?,?,?,?)",
                     (r.body.get("folder_id"), title, "link", url, "video" if "youtu" in url else "audio", 0, db.now()))
        jobs.add("info", iid, M("t_read_link", t=url), mode=r.body.get("mode") or db.get_settings().get("auto_download", "video"),
                 **({"q": int(r.body["q"])} if r.body.get("q") else {}))
        ids.append(iid)
    if not ids:
        raise HTTPError(400, "No links found")
    return {"ids": ids}


@route("POST", "/api/upload")
def upload(r):
    """One file per request; the raw file is the body (no multipart needed)."""
    name = media.safe_name(Path(r.query.get("name") or "file").name, 120)
    folder = r.query.get("folder_id")
    stem = re.sub(r"\s*\[(audio|video)\]", "", Path(name).stem).strip() or Path(name).stem
    d = media.unique(db.LIBRARY / media.safe_name(stem))
    d.mkdir(parents=True)
    dst = d / name
    left = int(r.headers.get("Content-Length") or 0)
    with open(dst, "wb") as out:
        while left > 0:
            chunk = r.rfile.read(min(left, 1 << 20))
            if not chunk:
                break
            out.write(chunk)
            left -= len(chunk)
    if left > 0:
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPError(400, "Upload was interrupted")
    dur, kind = media.probe(dst)
    iid = db.run("INSERT INTO items (folder_id, title, kind, file, media, duration, dir, created) VALUES (?,?,?,?,?,?,?,?)",
                 (int(folder) if folder else None, stem, "file", f"{d.name}/{name}", kind, dur, d.name, db.now()))
    return {"ids": [iid]}


def files_in(item):
    if not item["dir"]:
        return []
    d = db.LIBRARY / item["dir"]
    if not d.exists():
        return []
    return [{"path": p.relative_to(db.LIBRARY).as_posix(), "name": p.relative_to(d).as_posix(), "size": p.stat().st_size}
            for p in sorted(d.rglob("*")) if p.is_file() and not p.name.endswith((".part", ".ytdl", ".tmp"))]


@route("GET", "/api/items/(?P<iid>\\d+)")
def get_item(r, iid):
    iid = int(iid)
    i = db.one("SELECT * FROM items WHERE id=?", (iid,))
    if not i:
        raise HTTPError(404)
    i["bookmarks"] = db.q("SELECT * FROM bookmarks WHERE item_id=? ORDER BY start", (iid,))
    i["transcripts"] = db.q("SELECT id, bookmark_id, title, start, end, engine, file, created FROM transcripts "
                            "WHERE item_id=? ORDER BY start, id", (iid,))
    i["files"] = files_in(i)
    i["notes"] = db.q("SELECT * FROM notes WHERE item_id=? ORDER BY COALESCE(time, 1e12), id", (iid,))
    i["excerpts"] = db.q("SELECT * FROM excerpts WHERE item_id=? ORDER BY start", (iid,))
    i["projects"] = [x["project_id"] for x in db.q("SELECT project_id FROM project_items WHERE item_id=?", (iid,))]
    i["map"] = smart.get_map(iid)
    sp = jobs._speeds()
    i["jobs"] = [jobs.timing(dict(j, params=json.loads(j["params"] or "{}")), sp) for j in db.q(
        "SELECT id, kind, bookmark_id, title, status, progress, message, result, params, elapsed, run_start, media, "
        "speed_key, taken FROM jobs WHERE item_id=? "
        "AND status!='cancelled' ORDER BY id", (iid,))]
    return i


@route("PATCH", "/api/items/(?P<iid>\\d+)")
def patch_item(r, iid):
    b = r.body
    if b.get("title") is not None:
        db.run("UPDATE items SET title=? WHERE id=?", (b["title"].strip(), int(iid)))
    if b.get("move"):
        db.run("UPDATE items SET folder_id=? WHERE id=?", (b.get("folder_id"), int(iid)))
    if b.get("note") is not None:
        db.run("UPDATE items SET note=? WHERE id=?", (b["note"], int(iid)))
    if "pinned" in b:
        db.run("UPDATE items SET pinned=? WHERE id=?", (db.now() if b["pinned"] else None, int(iid)))
    if b.get("listen_pos") is not None:              # where the person stopped listening (kept for every device)
        db.run("UPDATE items SET listen_pos=?, listen_at=? WHERE id=?", (max(0.0, float(b["listen_pos"])), db.now(), int(iid)))
    if "listened" in b:                              # finished (automatically at the end, or by hand)
        db.run("UPDATE items SET listened=? WHERE id=?", (db.now() if b["listened"] else None, int(iid)))
    return {"ok": True}


@route("DELETE", "/api/items/(?P<iid>\\d+)")
def del_item(r, iid):
    iid = int(iid)
    i = db.one("SELECT * FROM items WHERE id=?", (iid,))
    if not i:
        return {"ok": True}
    for j in db.q("SELECT id FROM jobs WHERE item_id=? AND status IN ('queued','running','paused')", (iid,)):
        jobs.cancel(j["id"])
    db.run("DELETE FROM project_clips WHERE item_id=?", (iid,))
    db.run("DELETE FROM project_items WHERE item_id=?", (iid,))
    db.run("DELETE FROM excerpts WHERE item_id=?", (iid,))
    for t in ("bookmarks", "transcripts", "jobs", "notes"):
        db.run(f"DELETE FROM {t} WHERE item_id=?", (iid,))
    db.run("DELETE FROM items WHERE id=?", (iid,))
    if r.query.get("files") == "1" and i["dir"]:
        shutil.rmtree(db.LIBRARY / i["dir"], ignore_errors=True)
    return {"ok": True}


def num(v):
    return None if v is None or v == "" else float(v)


@route("POST", "/api/items/(?P<iid>\\d+)/bookmarks")
def add_mark(r, iid):
    start, end = num(r.body.get("start")), num(r.body.get("end"))
    if start is None:
        raise HTTPError(400, "Start is required")
    end = end if end is not None and end > start else None
    return {"id": db.run("INSERT INTO bookmarks (item_id, name, start, end, created) VALUES (?,?,?,?,?)",
                         (int(iid), (r.body.get("name") or "").strip(), start, end, db.now()))}


def locked(bid):
    m = db.one("SELECT done FROM bookmarks WHERE id=?", (bid,)) if bid else None
    return bool(m and m["done"])


@route("PATCH", "/api/bookmarks/(?P<bid>\\d+)")
def patch_mark(r, bid):
    b, bid = r.body, int(bid)
    if "done" in b:                      # the ✓ lock: only this can change a finished part
        db.run("UPDATE bookmarks SET done=? WHERE id=?", (1 if b["done"] else 0, bid))
        return {"ok": True}
    if locked(bid):
        raise HTTPError(423, "locked")
    if b.get("name") is not None:
        db.run("UPDATE bookmarks SET name=? WHERE id=?", (b["name"].strip(), bid))
    if b.get("start") is not None:
        db.run("UPDATE bookmarks SET start=? WHERE id=?", (num(b["start"]), bid))
    if b.get("end") is not None:
        db.run("UPDATE bookmarks SET end=? WHERE id=?", (num(b["end"]), bid))
    if b.get("note") is not None:
        db.run("UPDATE bookmarks SET note=? WHERE id=?", (b["note"], bid))
    if b.get("clear_end"):
        db.run("UPDATE bookmarks SET end=NULL WHERE id=?", (bid,))
    return {"ok": True}


@route("DELETE", "/api/bookmarks/(?P<bid>\\d+)")
def del_mark(r, bid):
    if locked(int(bid)):
        raise HTTPError(423, "locked")
    db.run("DELETE FROM bookmarks WHERE id=?", (int(bid),))
    return {"ok": True}


STD_HEIGHTS = [2160, 1440, 1080, 720, 480, 360, 240, 144]


@route("GET", "/api/items/(?P<iid>\\d+)/qualities")
def qualities(r, iid):
    """What can be downloaded: from the original picture down to the smallest, and MP3 bitrates."""
    i = db.one("SELECT * FROM items WHERE id=?", (int(iid),))
    if not i:
        raise HTTPError(404)
    src = jobs.local_source(i)
    local_h = media.video_height(src) if src and i["media"] == "video" else 0
    try:
        site = json.loads(i.get("heights") or "[]")
    except ValueError:
        site = []
    if i["url"] and i["media"] == "video" and not site and r.query.get("probe") == "1" and not local_h:
        site = media.link_heights(i["url"]) or []         # older links: ask the site once, quickly, and remember
        if site:
            db.run("UPDATE items SET heights=? WHERE id=?", (json.dumps(site), i["id"]))
    top = max([local_h] + site) if (local_h or site) else 0
    if i["media"] != "video":
        video = []
    elif site:
        video = [h for h in site if h >= 144]
    elif top:
        video = [top] + [h for h in STD_HEIGHTS if h < top]
    else:
        video = STD_HEIGHTS[2:]
    return {"video": video, "top": top, "local": local_h, "unknown": not (local_h or site),
            "audio": [0, 192, 128, 96, 64]}


@route("POST", "/api/items/(?P<iid>\\d+)/action")
def item_action(r, iid):
    iid = int(iid)
    i = db.one("SELECT * FROM items WHERE id=?", (iid,))
    if not i:
        raise HTTPError(404)
    t, a = i["title"], r.body.get("action")
    if a == "fetch_audio":
        jobs.add("fetch", iid, M("t_dl_audio", t=t), want="audio")
    elif a == "fetch_video":
        q = int(r.body.get("q") or 0)
        jobs.add("fetch", iid, M("t_dl_video", t=t) + (f" · {q}p" if q else ""), want="video", **({"height": q} if q else {}))
    elif a == "convert":
        jobs.add("convert", iid, M("t_convert", t=t))
    elif a == "transcribe":
        jobs.add("transcribe", iid, M("t_tx_all", t=t))
    elif a == "map":
        if not export.item_segments(iid):
            raise HTTPError(400, M("map_need_tr"))
        db.run("UPDATE jobs SET status='cancelled' WHERE kind='map' AND item_id=? AND status IN ('queued','error','paused')", (iid,))
        jobs.add("map", iid, M("t_map", t=t))
    else:
        raise HTTPError(400)
    return {"ok": True}


@route("POST", "/api/clipfile")
def clip_file(r):
    """Everything about one finished part file: rename it, cut it again with new times,
    transcribe it, or delete it. The file is found through the job that made it."""
    b = r.body
    path = (b.get("path") or "").strip()
    j = db.one("SELECT * FROM jobs WHERE kind='clip' AND result=? ORDER BY id DESC", (path,))
    if not j:
        raise HTTPError(404, "clip not found")
    p = json.loads(j["params"] or "{}")
    i = db.one("SELECT * FROM items WHERE id=?", (j["item_id"],))
    act = b.get("action")
    f = (db.LIBRARY / path).resolve()
    if db.LIBRARY.resolve() not in f.parents:
        raise HTTPError(400)
    if act == "info":
        return {"item_id": j["item_id"], "item_title": i and i["title"], "start": p.get("start"), "end": p.get("end"),
                "name": p.get("name") or "", "fmt": p.get("fmt", "mp3"), "bookmark_id": j["bookmark_id"],
                "excerpt_id": p.get("excerpt_id"), "path": path, "locked": locked(j["bookmark_id"]),
                "src": i and i["file"], "media": i and i["media"], "duration": i and i["duration"]}
    if act in ("rename", "recut", "delete") and locked(j["bookmark_id"]):
        raise HTTPError(423, "locked")
    if act == "rename":
        name = (b.get("name") or "").strip()
        if not name:
            raise HTTPError(400, "name required")
        new = f
        if f.exists():
            new = media.unique(f.with_name(media.safe_name(name) + f.suffix))
            if new.name != f.name:
                f.rename(new)
        rel = new.relative_to(db.LIBRARY).as_posix()
        p["name"] = name
        db.run("UPDATE jobs SET result=?, params=? WHERE id=?", (rel, json.dumps(p), j["id"]))
        for o in db.q("SELECT id, bookmark_id, params, result FROM jobs WHERE kind='clip' AND status='done' "
                      "AND id!=? AND item_id=? AND result IS NOT NULL AND result!=''", (j["id"], j["item_id"])):
            op = json.loads(o["params"] or "{}")
            same = (j["bookmark_id"] and o["bookmark_id"] == j["bookmark_id"]) or \
                   (p.get("excerpt_id") and op.get("excerpt_id") == p.get("excerpt_id"))
            of = db.LIBRARY / o["result"]
            if not same or not of.is_file():
                continue
            nf = media.unique(of.with_name(media.safe_name(name) + of.suffix))
            if nf.name != of.name:
                of.rename(nf)
            op["name"] = name
            db.run("UPDATE jobs SET result=?, params=? WHERE id=?", (nf.relative_to(db.LIBRARY).as_posix(), json.dumps(op), o["id"]))
        if j["bookmark_id"]:
            db.run("UPDATE bookmarks SET name=? WHERE id=?", (name, j["bookmark_id"]))
        if p.get("excerpt_id"):
            db.run("UPDATE excerpts SET title=? WHERE id=?", (name, p["excerpt_id"]))
        return {"path": rel}
    if act == "recut":
        a, e = num(b.get("start")), num(b.get("end"))
        if a is None or e is None or e <= a:
            raise HTTPError(400, "bad times")
        if j["bookmark_id"]:
            db.run("UPDATE bookmarks SET start=?, end=? WHERE id=?", (a, e, j["bookmark_id"]))
        if p.get("excerpt_id"):
            db.run("UPDATE excerpts SET start=?, end=? WHERE id=?", (a, e, p["excerpt_id"]))
        f.unlink(missing_ok=True)
        db.run("UPDATE jobs SET result=NULL WHERE id=?", (j["id"],))
        label = p.get("name") or media.short_time(a)
        extra = {"excerpt_id": p["excerpt_id"]} if p.get("excerpt_id") else {}
        jobs.add("clip", i["id"], M("t_mp3_part" if p.get("fmt", "mp3") == "mp3" else "t_video_part", l=label, t=i["title"]),
                 j["bookmark_id"], fmt=p.get("fmt", "mp3"), start=a, end=e, name=p.get("name"), **extra, **({"q": p["q"]} if p.get("q") else {}),
                 **({"nosil": 1} if p.get("nosil") else {}))
        return {"ok": True}
    if act == "transcribe":
        label = p.get("name") or media.short_time(p.get("start") or 0)
        jobs.add("transcribe", i["id"], M("t_tx_part", l=label, t=i["title"]), j["bookmark_id"],
                 start=p.get("start"), end=p.get("end"), name=p.get("name"))
        return {"ok": True}
    if act == "delete":
        f.unlink(missing_ok=True)
        db.run("UPDATE jobs SET result=NULL WHERE id=?", (j["id"],))
        return {"ok": True}
    raise HTTPError(400, "unknown action")


@route("POST", "/api/bookmarks/action")
def marks_action(r):
    n, action = 0, r.body.get("action")
    for bid in r.body.get("ids") or []:
        m = db.one("SELECT * FROM bookmarks WHERE id=?", (int(bid),))
        if not m:
            continue
        i = db.one("SELECT * FROM items WHERE id=?", (m["item_id"],))
        end = m["end"] or i["duration"] or None
        label = m["name"] or media.short_time(m["start"])
        common = dict(start=m["start"], end=end, name=m["name"])
        if action in ("mp3", "video"):
            q = int(r.body.get("q") or 0)
            tag = (f" · {q}p" if action == "video" else f" · {q}k") if q else ""
            ns = {"nosil": 1} if r.body.get("nosil") else {}
            tag += f" · {M('nosil_name')}" if ns else ""
            jobs.add("clip", i["id"], M("t_mp3_part" if action == "mp3" else "t_video_part", l=label, t=i["title"]) + tag,
                     m["id"], fmt=action, **common, **({"q": q} if q else {}), **ns)
        elif action == "transcribe":
            jobs.add("transcribe", i["id"], M("t_tx_part", l=label, t=i["title"]), m["id"], **common)
        n += 1
    return {"queued": n}


@route("GET", "/api/transcripts/(?P<tid>\\d+)")
def get_transcript(r, tid):
    t = db.one("SELECT * FROM transcripts WHERE id=?", (int(tid),))
    if not t:
        raise HTTPError(404)
    t["segments"] = json.loads(t["segments"] or "[]")
    return t


@route("DELETE", "/api/transcripts/(?P<tid>\\d+)")
def del_transcript(r, tid):
    db.run("DELETE FROM transcripts WHERE id=?", (int(tid),))
    return {"ok": True}


# ---------- transcript editing ----------
@route("PATCH", r"/api/transcripts/(?P<tid>\d+)")
def patch_transcript(r, tid):
    t = db.one("SELECT * FROM transcripts WHERE id=?", (int(tid),))
    if not t:
        raise HTTPError(404)
    if r.body.get("title") is not None:
        db.run("UPDATE transcripts SET title=? WHERE id=?", (r.body["title"].strip(), t["id"]))
    if r.body.get("segments") is not None:
        segs = [{"start": float(x["start"]), "end": float(x["end"]), "text": str(x["text"]).strip()}
                for x in r.body["segments"] if str(x.get("text", "")).strip()]
        db.run("UPDATE transcripts SET segments=?, text=? WHERE id=?",
               (json.dumps(segs, ensure_ascii=False), " ".join(x["text"] for x in segs), t["id"]))
        jobs.write_files(db.one("SELECT * FROM transcripts WHERE id=?", (t["id"],)))
    return {"ok": True}


@route("GET", r"/api/items/(?P<iid>\d+)/segments")
def item_segments(r, iid):
    return export.item_segments(int(iid))


# ---------- notes & benefits ----------
@route("POST", r"/api/items/(?P<iid>\d+)/notes")
def add_note(r, iid):
    return {"id": db.run("INSERT INTO notes (item_id, text, time, created, updated) VALUES (?,?,?,?,?)",
                         (int(iid), (r.body.get("text") or "").strip(), num(r.body.get("time")), db.now(), db.now()))}


@route("PATCH", r"/api/notes/(?P<nid>\d+)")
def patch_note(r, nid):
    if r.body.get("text") is not None:
        db.run("UPDATE notes SET text=?, updated=? WHERE id=?", (r.body["text"].strip(), db.now(), int(nid)))
    if "time" in r.body:
        db.run("UPDATE notes SET time=? WHERE id=?", (num(r.body["time"]), int(nid)))
    return {"ok": True}


@route("DELETE", r"/api/notes/(?P<nid>\d+)")
def del_note(r, nid):
    db.run("DELETE FROM notes WHERE id=?", (int(nid),))
    return {"ok": True}


# ---------- excerpts: titled parts of a transcript ----------
@route("POST", r"/api/items/(?P<iid>\d+)/excerpts")
def add_excerpt(r, iid):
    a, b = num(r.body.get("start")), num(r.body.get("end"))
    if a is None or b is None or b <= a:
        raise HTTPError(400, "bad range")
    text = " ".join(x["text"] for x in export.item_segments(int(iid), a, b))
    return {"id": db.run("INSERT INTO excerpts (item_id, start, end, title, text, note, created) VALUES (?,?,?,?,?,?,?)",
                         (int(iid), a, b, (r.body.get("title") or "").strip(), text, r.body.get("note") or "", db.now()))}


@route("PATCH", r"/api/excerpts/(?P<xid>\d+)")
def patch_excerpt(r, xid):
    for k in ("title", "note"):
        if r.body.get(k) is not None:
            db.run(f"UPDATE excerpts SET {k}=? WHERE id=?", (str(r.body[k]).strip(), int(xid)))
    return {"ok": True}


@route("DELETE", r"/api/excerpts/(?P<xid>\d+)")
def del_excerpt(r, xid):
    db.run("DELETE FROM excerpts WHERE id=?", (int(xid),))
    return {"ok": True}


@route("POST", r"/api/excerpts/(?P<xid>\d+)/clip")
def clip_excerpt(r, xid):
    x = db.one("SELECT * FROM excerpts WHERE id=?", (int(xid),))
    i = db.one("SELECT * FROM items WHERE id=?", (x["item_id"],))
    fmt, q = r.body.get("fmt", "mp3"), int(r.body.get("q") or 0)
    label = x["title"] or media.short_time(x["start"])
    ns = {"nosil": 1} if r.body.get("nosil") else {}
    jobs.add("clip", i["id"], M("t_mp3_part" if fmt == "mp3" else "t_video_part", l=label, t=i["title"]) + (f" · {M('nosil_name')}" if ns else ""), None,
             fmt=fmt, start=x["start"], end=x["end"], name=x["title"], excerpt_id=x["id"], **({"q": q} if q else {}), **ns)
    return {"ok": True}


# ---------- silences: jump over them while listening, or make a copy without them ----------
def _lib_file(path):
    f = (db.LIBRARY / (path or "")).resolve()
    if db.LIBRARY.resolve() not in f.parents or not f.is_file():
        raise HTTPError(404, "file not found")
    return f


def _item_of_file(path, iid):
    if iid:
        return db.one("SELECT * FROM items WHERE id=?", (int(iid),))
    top = (path or "").split("/")[0]
    return db.one("SELECT * FROM items WHERE dir=?", (top,))


@route("GET", "/api/silence")
def get_silence(r):
    """The silences of a file, for the player. Measured once in the background (a short task)."""
    path = r.query.get("path") or ""
    f = _lib_file(path)
    lv = silence.cached(f)
    s = db.get_settings()
    if lv:
        sp = silence.spans(silence.levels(lv), float(r.query.get("min") or s.get("sil_min") or 0.3),
                           r.query.get("sens") or s.get("sil_sens") or "normal")
        return {"spans": sp, "saved": round(sum(b - a for a, b in sp), 1)}
    for j in db.q("SELECT id, status, params, message FROM jobs WHERE kind='levels' ORDER BY id DESC LIMIT 30"):
        if json.loads(j["params"] or "{}").get("path") == path:
            if j["status"] in ("queued", "running"):
                return {"pending": True}
            if j["status"] == "error" and not r.query.get("retry"):
                return {"error": j["message"]}
            break
    item = _item_of_file(path, r.query.get("item"))
    if not item:
        raise HTTPError(404, "lesson not found")
    jobs.add("levels", item["id"], M("t_levels", t=item["title"]), path=path)
    return {"pending": True}


@route("POST", "/api/nosil")
def make_nosil(r):
    """A copy of a downloaded file (whole lesson or a part) without its silences."""
    path = r.body.get("path") or ""
    f = _lib_file(path)
    item = _item_of_file(path, r.body.get("item_id"))
    if not item:
        raise HTTPError(404, "lesson not found")
    jobs.add("nosil", item["id"], M("t_nosil", t=f.stem), path=path)
    return {"ok": True}


# ---------- what a folder holds: lessons, parts, excerpts ----------
@route("GET", r"/api/folders/(?P<fid>\w+)/contents")
def folder_contents(r, fid):
    if fid not in ("all", "none") and not fid.isdigit():
        raise HTTPError(404)
    where = "" if fid == "all" else ("WHERE i.folder_id IS NULL" if fid == "none" else "WHERE i.folder_id=?")
    args = () if fid in ("all", "none") else (int(fid),)
    marks = db.q("SELECT b.*, i.title AS item_title, i.media AS media, i.kind AS kind FROM bookmarks b "
                 f"JOIN items i ON i.id=b.item_id {where} ORDER BY i.id DESC, b.start", args)
    ex = db.q("SELECT x.*, i.title AS item_title FROM excerpts x JOIN items i ON i.id=x.item_id "
              f"{where} ORDER BY i.id DESC, x.start", args)
    sp = jobs._speeds()
    js = [jobs.timing(dict(j, params=json.loads(j["params"] or "{}")), sp) for j in db.q(
        "SELECT id, kind, item_id, bookmark_id, status, progress, result, params, elapsed, run_start, media, "
        "speed_key, taken FROM jobs "
        "WHERE kind='clip' AND status!='cancelled' ORDER BY id")]
    ids = {i["id"] for i in db.q(f"SELECT i.id FROM items i {where}", args)}
    titles = {i["id"]: i["title"] for i in db.q("SELECT id, title FROM items")}
    works = []
    for j in db.q("SELECT id, item_id, bookmark_id, params, result, taken, updated FROM jobs "
                  "WHERE kind='clip' AND status='done' AND result!='' AND result IS NOT NULL ORDER BY id DESC"):
        f = db.LIBRARY / j["result"]
        if j["item_id"] in ids and f.is_file():
            p = json.loads(j["params"] or "{}")
            works.append({"type": "video" if p.get("fmt") == "video" else "audio", "path": j["result"], "item_id": j["item_id"],
                          "item_title": titles.get(j["item_id"]), "start": p.get("start"), "end": p.get("end"),
                          "name": f.stem, "size": f.stat().st_size, "locked": locked(j["bookmark_id"]), "t": j["updated"]})
    for t in db.q("SELECT id, item_id, bookmark_id, title, start, end, file, created FROM transcripts ORDER BY id DESC"):
        if t["item_id"] in ids:
            works.append({"type": "tr", "id": t["id"], "item_id": t["item_id"], "item_title": titles.get(t["item_id"]),
                          "start": t["start"], "end": t["end"], "name": t["title"], "path": t["file"], "t": t["created"],
                          "locked": locked(t["bookmark_id"])})
    works.sort(key=lambda w: -(w["t"] or 0))
    return {"marks": marks, "excerpts": ex, "jobs": js, "works": works}


# ---------- lessons inside projects ----------
@route("POST", r"/api/projects/(?P<pid>\d+)/items")
def add_project_item(r, pid):
    db.run("INSERT OR IGNORE INTO project_items (project_id, item_id, created) VALUES (?,?,?)",
           (int(pid), int(r.body["item_id"]), db.now()))
    return {"ok": True}


@route("DELETE", r"/api/projects/(?P<pid>\d+)/items/(?P<iid>\d+)")
def del_project_item(r, pid, iid):
    db.run("DELETE FROM project_items WHERE project_id=? AND item_id=?", (int(pid), int(iid)))
    return {"ok": True}


# ---------- search across everything ----------
@route("GET", "/api/search")
def do_search(r):
    return search.search(r.query.get("q", ""), r.query.get("folder"))


# ---------- topic projects ----------
@route("GET", "/api/projects")
def list_projects(r):
    return db.q("SELECT p.*, (SELECT COUNT(*) FROM project_clips c WHERE c.project_id=p.id) AS clips, "
                "(SELECT COALESCE(SUM(c.end-c.start),0) FROM project_clips c WHERE c.project_id=p.id) AS seconds, "
                "(SELECT COUNT(*) FROM project_items pi WHERE pi.project_id=p.id) AS items "
                "FROM projects p ORDER BY p.id DESC")


@route("POST", "/api/projects")
def new_project(r):
    return {"id": db.run("INSERT INTO projects (name, description, created) VALUES (?,?,?)",
                         ((r.body.get("name") or "").strip() or "Project", r.body.get("description") or "", db.now()))}


@route("GET", r"/api/projects/(?P<pid>\d+)")
def get_project(r, pid):
    p = db.one("SELECT * FROM projects WHERE id=?", (int(pid),))
    if not p:
        raise HTTPError(404)
    p["clips"] = db.q("SELECT c.*, i.title AS item_title, i.thumb AS thumb FROM project_clips c "
                      "LEFT JOIN items i ON i.id=c.item_id WHERE project_id=? ORDER BY pos, id", (p["id"],))
    for c in p["clips"]:
        c["excerpt"] = " ".join(s["text"] for s in export.item_segments(c["item_id"], c["start"], c["end"]))[:400]
    try:
        p["sections"] = json.loads(p.get("sections") or "[]")
    except ValueError:
        p["sections"] = []
    for c in p["clips"]:
        if c.get("section") and c["section"] not in p["sections"]:
            p["sections"].append(c["section"])
    p["items"] = db.q("SELECT i.* FROM project_items pi JOIN items i ON i.id=pi.item_id WHERE pi.project_id=? "
                      "ORDER BY pi.created", (p["id"],))
    p["jobs"] = [j for j in db.q("SELECT id, status, progress, message, result, elapsed, run_start, media, speed_key, "
                                 "taken, params FROM jobs WHERE kind='project' ORDER BY id DESC")
                 if json.loads(j.pop("params") or "{}").get("project_id") == p["id"]][:1]
    p["jobs"] = [jobs.timing(j) for j in p["jobs"]]
    return p


@route("PATCH", r"/api/projects/(?P<pid>\d+)")
def patch_project(r, pid):
    for k in ("name", "description"):
        if r.body.get(k) is not None:
            db.run(f"UPDATE projects SET {k}=? WHERE id=?", (r.body[k].strip(), int(pid)))
    if isinstance(r.body.get("sections"), list):
        secs = [str(x).strip() for x in r.body["sections"] if str(x).strip()]
        db.run("UPDATE projects SET sections=? WHERE id=?", (json.dumps(secs, ensure_ascii=False), int(pid)))
    if r.body.get("rename_section"):
        a, b = r.body["rename_section"]
        db.run("UPDATE project_clips SET section=? WHERE project_id=? AND section=?", (b or None, int(pid), a))
    return {"ok": True}


@route("DELETE", r"/api/projects/(?P<pid>\d+)")
def del_project(r, pid):
    db.run("DELETE FROM project_clips WHERE project_id=?", (int(pid),))
    db.run("DELETE FROM project_items WHERE project_id=?", (int(pid),))
    db.run("DELETE FROM projects WHERE id=?", (int(pid),))
    return {"ok": True}


@route("POST", r"/api/projects/(?P<pid>\d+)/clips")
def add_pclip(r, pid):
    b = r.body
    pos = (db.one("SELECT MAX(pos) m FROM project_clips WHERE project_id=?", (int(pid),))["m"] or 0) + 1
    return {"id": db.run("INSERT INTO project_clips (project_id, item_id, start, end, title, note, pos, created, section) "
                         "VALUES (?,?,?,?,?,?,?,?,?)", (int(pid), int(b["item_id"]), num(b["start"]), num(b["end"]),
                                                        (b.get("title") or "").strip(), b.get("note") or "", pos, db.now(),
                                                        (b.get("section") or "").strip() or None))}


@route("PATCH", r"/api/pclips/(?P<cid>\d+)")
def patch_pclip(r, cid):
    for k in ("title", "note"):
        if r.body.get(k) is not None:
            db.run(f"UPDATE project_clips SET {k}=? WHERE id=?", (r.body[k], int(cid)))
    if "section" in r.body:
        db.run("UPDATE project_clips SET section=? WHERE id=?", ((r.body["section"] or "").strip() or None, int(cid)))
    for k in ("start", "end"):
        if r.body.get(k) is not None:
            db.run(f"UPDATE project_clips SET {k}=? WHERE id=?", (num(r.body[k]), int(cid)))
    return {"ok": True}


@route("DELETE", r"/api/pclips/(?P<cid>\d+)")
def del_pclip(r, cid):
    db.run("DELETE FROM project_clips WHERE id=?", (int(cid),))
    return {"ok": True}


@route("POST", r"/api/pclips/(?P<cid>\d+)/move")
def move_pclip(r, cid):
    c = db.one("SELECT * FROM project_clips WHERE id=?", (int(cid),))
    rows = db.q("SELECT id FROM project_clips WHERE project_id=? ORDER BY pos, id", (c["project_id"],))
    ids = [x["id"] for x in rows]
    i = ids.index(c["id"])
    j = max(0, min(len(ids) - 1, i + int(r.body.get("dir", 1))))
    ids.insert(j, ids.pop(i))
    for n, x in enumerate(ids):
        db.run("UPDATE project_clips SET pos=? WHERE id=?", (n, x))
    return {"ok": True}


@route("POST", r"/api/projects/(?P<pid>\d+)/export")
def export_project(r, pid):
    p = db.one("SELECT * FROM projects WHERE id=?", (int(pid),))
    jid = jobs.add("project", None, M("t_project", t=p["name"]), project_id=p["id"], fmt=r.body.get("fmt", "mp3"))
    return {"job": jid}


# ---------- book export: PDF (print), Word, text ----------
def export_opts(q):
    return {"title": q.get("title") or None, "subtitle": q.get("subtitle"), "author": q.get("author") or "",
            "ts": q.get("ts") == "1", "notes": q.get("notes", "1") == "1", "cover": q.get("cover", "1") == "1",
            "toc": q.get("toc", "1") == "1", "mode": q.get("mode", "auto"), "size": q.get("size", "m"),
            "font": q.get("font") or db.get_settings().get("font_read") or "amiri",
            "hfont": q.get("hfont") or q.get("font") or db.get_settings().get("font_read") or "amiri",
            "accent": db.get_settings().get("accent")}


# ---------- your own paragraphs for an exported transcript: title + start + end each ----------
def _para_source(scope):
    kind, sid = scope.split(":")
    if kind == "tr":
        t = db.one("SELECT segments FROM transcripts WHERE id=?", (int(sid),))
        return json.loads(t["segments"] or "[]") if t else []
    return export.item_segments(int(sid))


@route("GET", "/api/paras")
def get_paras(r):
    scope = r.query.get("scope", "")
    if not re.fullmatch(r"(tr|item):\d+", scope):
        raise HTTPError(400, "scope must look like item:3 or tr:5")
    segs = _para_source(scope)
    row = db.one("SELECT data FROM paras WHERE scope=?", (scope,))
    if row:
        return {"custom": True, "paras": json.loads(row["data"]), "segs": segs}
    auto = export.paragraphs(segs, "auto")
    return {"custom": False, "segs": segs,
            "paras": [{"title": "", "start": p["t"], "end": p["e"]} for p in auto]}


@route("POST", "/api/paras")
def save_paras(r):
    scope, ps = r.body.get("scope", ""), r.body.get("paras")
    if ps is None:
        db.run("DELETE FROM paras WHERE scope=?", (scope,))
        return {"ok": True}
    clean = sorted([{"title": (p.get("title") or "").strip(), "start": float(p["start"]), "end": float(p["end"])}
                    for p in ps if p.get("end") is not None and float(p["end"]) > float(p["start"])], key=lambda p: p["start"])
    db.run("INSERT OR REPLACE INTO paras (scope, data) VALUES (?,?)", (scope, json.dumps(clean, ensure_ascii=False)))
    return {"ok": True}


@route("GET", "/export")
def export_book(r):
    q = r.query
    book = export.build(q.get("src", "item"), int(q.get("id", 0)), q.get("which", "full"))
    o = export_opts(q)
    fmt = q.get("fmt", "html")
    if fmt == "docx":
        return Raw(export.render_docx(book, o), "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                   export.filename(book, o, "docx"))
    if fmt == "txt":
        return Raw(export.render_txt(book, o).encode("utf-8"), "text/plain; charset=utf-8", export.filename(book, o, "txt"))
    return Raw(export.render_html(book, o, auto_print=q.get("print") == "1").encode("utf-8"), "text/html; charset=utf-8")


# ---------- updating the app from a new zip (no typing needed) ----------
def _find_update():
    """Newest Maqati zip or unzipped folder in the Download folder."""
    homes = [Path.home() / "storage" / "downloads", Path.home() / "Downloads", Path.home() / "Download"]
    found = []
    for h in homes:
        if not h.is_dir():
            continue
        for z in h.glob("maqati*.zip"):
            found.append((z.stat().st_mtime, z))
        for v in list(h.glob("maqati*/app/version.py")) + list(h.glob("maqati*/maqati*/app/version.py")):
            found.append((v.stat().st_mtime, v.parent.parent))
    return max(found)[1] if found else None


def _install_from(src):
    import tempfile
    import zipfile
    tmp = Path(tempfile.mkdtemp(prefix="maqati-up-"))
    try:
        if src.is_file():
            with zipfile.ZipFile(src) as z:
                z.extractall(tmp)
            roots = [p.parent.parent for p in tmp.rglob("app/version.py")]
            root = roots[0] if roots else None
        else:
            root = src
        if not root or not (root / "app" / "main.py").exists():
            raise HTTPError(400, "This is not a Maqati update")
        ns = {}
        exec((root / "app" / "version.py").read_text(encoding="utf-8"), ns)
        me = Path(__file__).resolve().parent.parent
        shutil.rmtree(me / "app.old", ignore_errors=True)
        shutil.copytree(me / "app", me / "app.old")
        shutil.copytree(root / "app", me / "app", dirs_exist_ok=True)
        for f in root.iterdir():
            if f.is_file() and f.suffix in (".txt", ".sh", ".bat", ".command"):
                shutil.copy2(f, me / f.name)
        return ns.get("VERSION", "?")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _restart():
    def go():
        import time
        time.sleep(1.2)
        jobs.stop_all()
        time.sleep(0.8)
        os.environ["MAQATI_OPEN"] = "0"
        os.chdir(Path(__file__).resolve().parent.parent)
        os.execv(sys.executable, [sys.executable, "-m", "app.main"])
    threading.Thread(target=go, daemon=True).start()


@route("GET", "/api/update/check")
def update_check(r):
    if HOSTED:
        return {"found": False}
    f = _find_update()
    if not f:
        return {"found": False}
    ver = None
    try:
        if f.is_file():
            import zipfile
            with zipfile.ZipFile(f) as z:
                names = [n for n in z.namelist() if n.endswith("app/version.py")]
                if names:
                    ns = {}
                    exec(z.read(names[0]).decode("utf-8"), ns)
                    ver = ns.get("VERSION")
        else:
            ns = {}
            exec((f / "app" / "version.py").read_text(encoding="utf-8"), ns)
            ver = ns.get("VERSION")
    except Exception:
        pass
    return {"found": True, "name": f.name, "version": ver, "current": VERSION}


@route("POST", "/api/update/auto")
def update_auto(r):
    if HOSTED:
        raise HTTPError(400, M("hosted_disabled"))
    f = _find_update()
    if not f:
        raise HTTPError(404, "No Maqati zip found in Download")
    v = _install_from(f)
    _restart()
    return {"ok": True, "version": v}


@route("POST", "/api/update/upload")
def update_upload(r):
    if HOSTED:
        raise HTTPError(400, M("hosted_disabled"))
    import tempfile
    n = int(r.headers.get("Content-Length") or 0)
    fd, name = tempfile.mkstemp(suffix=".zip")
    with os.fdopen(fd, "wb") as out:
        while n > 0:
            chunk = r.rfile.read(min(n, 1 << 20))
            if not chunk:
                break
            out.write(chunk)
            n -= len(chunk)
    try:
        v = _install_from(Path(name))
    finally:
        os.unlink(name)
    _restart()
    return {"ok": True, "version": v}


# ---------- tasks ----------
@route("GET", "/api/jobs")
def list_jobs(r):
    sp, now = jobs._speeds(), time.time()
    out = [jobs.timing(j, sp, now) for j in db.q(
                "SELECT id, kind, item_id, bookmark_id, title, status, progress, message, result, created, "
                "elapsed, run_start, media, speed_key, taken, params FROM jobs WHERE COALESCE(hidden,0)=0 ORDER BY CASE status WHEN 'running' THEN 0 WHEN 'queued' THEN 1 "
                "WHEN 'paused' THEN 2 WHEN 'error' THEN 3 ELSE 4 END, id DESC LIMIT 300")]
    for j in out:
        p = j.pop("params", None)
        if j["kind"] == "project":
            j["project_id"] = json.loads(p or "{}").get("project_id")
    return out


@route("POST", "/api/jobs/(?P<jid>\\d+)/(?P<op>\\w+)")
def job_op(r, jid, op):
    jid = int(jid)
    if op == "pause":
        jobs.pause(jid)
    elif op in ("resume", "retry"):
        jobs.resume(jid)
    elif op == "cancel":
        jobs.cancel(jid)
    else:
        raise HTTPError(400)
    return {"ok": True}


@route("POST", "/api/jobs-clear")
def clear_jobs(r):
    db.run("DELETE FROM jobs WHERE status='cancelled' OR (status='done' AND (result IS NULL OR result=''))")
    db.run("UPDATE jobs SET hidden=1 WHERE status='done'")
    return {"ok": True}


@route("POST", "/api/jobs-all/(?P<op>\\w+)")
def all_jobs(r, op):
    if op == "pause":
        for j in db.q("SELECT id FROM jobs WHERE status IN ('queued','running')"):
            jobs.pause(j["id"])
    elif op == "resume":
        db.run("UPDATE jobs SET status='queued', message='Waiting' WHERE status='paused'")
        jobs._wake.set()
    return {"ok": True}


# ---------- settings & health ----------
@route("GET", "/api/settings")
def get_settings(r):
    s = db.get_settings()
    s["groq_key_set"] = bool(s.pop("groq_key"))
    s.pop("lan_code", None)
    return s


@route("POST", "/api/settings")
def save_settings(r):
    b = {k: v for k, v in r.body.items() if not k.startswith("lan_")}
    if not b.get("groq_key"):
        b.pop("groq_key", None)
    db.set_settings(b)
    return {"ok": True}


_update = {"running": False, "msg": ""}


@route("GET", "/api/health")
def health(r):
    ver = media.ytdlp_version()
    return {"version": VERSION, "apk": APK, "cookies": bool(media.cookies_file()), "ffmpeg": bool(media.FFMPEG), "ytdlp": ver, "offline_engine": transcribe.engine_ok(),
            "js": media.JS_RUNTIME, "library": "-" if HOSTED else str(db.LIBRARY), "update": _update, "android": ANDROID,
            "hosted": HOSTED, "desktop": DESKTOP, "user": os.environ.get("MAQATI_USERNAME") if HOSTED else None}


@route("POST", "/api/test-transcription")
def test_transcription(r):
    """One-tap check: key saved? Groq reachable? a real 3-second transcription works?"""
    import tempfile
    import requests
    ar = db.get_settings().get("lang") != "en"
    s = db.get_settings()
    steps = []

    def add(ok, ar_msg, en_msg):
        steps.append({"ok": ok, "msg": ar_msg if ar else en_msg})
        return ok
    if s.get("engine") == "local":
        return {"steps": [{"ok": transcribe.engine_ok(), "msg": "local engine"}]}
    key = (s.get("groq_key") or "").strip()
    if not add(bool(key), "مفتاح Groq محفوظ" if key else "لا يوجد مفتاح Groq — الصقه في الإعدادات",
               "Groq key saved" if key else "No Groq key — paste it in Settings"):
        return {"steps": steps}
    try:
        rr = requests.get(transcribe.GROQ_URL.rsplit("/audio/", 1)[0] + "/models",
                          headers={"Authorization": f"Bearer {key}"}, timeout=20)
        if rr.status_code in (401, 403):
            add(False, "Groq رفض المفتاح — أنشئ مفتاحًا جديدًا والصقه", "Groq rejected the key — create a new one")
            return {"steps": steps}
        add(rr.status_code < 400 or rr.status_code == 404, f"الاتصال بـ Groq يعمل ({rr.status_code})",
            f"Groq reachable ({rr.status_code})")
    except Exception as e:
        add(False, f"تعذّر الوصول إلى Groq: {e}", f"Cannot reach Groq: {e}")
        return {"steps": steps}
    tmp = Path(tempfile.mkdtemp()) / "test.mp3"
    try:
        media.ffmpeg(["-f", "lavfi", "-i", "sine=frequency=300:duration=3", "-ac", "1", "-ar", "16000",
                      "-c:a", "libmp3lame", "-b:a", "48k", str(tmp)])
        add(True, "ffmpeg يجهّز الصوت", "ffmpeg prepares audio")
    except Exception as e:
        add(False, f"ffmpeg لا يعمل: {e}", f"ffmpeg failed: {e}")
        return {"steps": steps}
    try:
        transcribe.groq(tmp, s)
        add(True, "تجربة تفريغ حقيقية نجحت ✓ — التفريغ جاهز", "A real test transcription worked ✓")
    except Exception as e:
        add(False, f"فشلت تجربة التفريغ: {e}", f"Test transcription failed: {e}")
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)
    return {"steps": steps}


@route("POST", "/api/test-mirrors")
def test_mirrors(r):
    from . import mirrors
    res = mirrors.check_all()
    return {"servers": [{"server": s.split("//")[1], "ok": ok, "title": t} for s, ok, t in res]}


@route("POST", "/api/test-youtube")
def test_youtube(r):
    """Try to read one well-known video every way the app knows, and say exactly what happened (for the owner's screenshots)."""
    steps = []
    add = lambda ok, ar, en: steps.append({"ok": ok, "text": ar if ui_lang() != "en" else en})
    ver = media.ytdlp_version()
    add(bool(ver), f"أداة التنزيل yt-dlp: {ver or 'غير موجودة'}", f"yt-dlp: {ver or 'missing'}")
    js = media.JS_RUNTIME
    add(bool(js), f"مساعد JavaScript: {js or 'غير موجود (يحتاجه يوتيوب)'}", f"JavaScript helper: {js or 'missing (YouTube needs it)'}")
    add(bool(media.FFMPEG), "ffmpeg موجود" if media.FFMPEG else "ffmpeg غير موجود", "ffmpeg found" if media.FFMPEG else "ffmpeg missing")
    add(bool(media.cookies_file()), "ملف كوكيز: " + ("موجود" if media.cookies_file() else "لا يوجد (اختياري)"), "cookies file: " + ("yes" if media.cookies_file() else "none (optional)"))
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    tried = []
    for alt in range(len(media.ALTS)):
        try:
            out = subprocess.run(media.ytdlp_base(alt) + ["-J", "--skip-download", url], capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=120, creationflags=media.NO_WINDOW, env=media.UTF8_ENV)
        except Exception as e:
            tried.append(f"{' '.join(media.ALTS[alt]) or 'default'}: {e}")
            continue
        if out.returncode == 0:
            title = json.loads(out.stdout).get("title")
            add(True, f"يوتيوب يعمل ✓ ({' '.join(media.ALTS[alt]) or 'الطريقة العادية'}) — «{title}»", f"YouTube works ✓ ({' '.join(media.ALTS[alt]) or 'default'}) — “{title}”")
            return {"steps": steps, "tried": tried}
        lines = [l for l in out.stderr.splitlines() if "ERROR" in l or "WARNING" in l]
        tried.append(f"{' '.join(media.ALTS[alt]) or 'default'}: {(lines[-1] if lines else out.stderr[-200:]).strip()[:300]}")
    add(False, "يوتيوب رفض كل الطرق. التفاصيل أدناه.", "YouTube refused every way in. Details below.")
    return {"steps": steps, "tried": tried}


@route("POST", "/api/cookies")
def set_cookies(r):
    n = int(r.headers.get("Content-Length") or 0)
    data = r.rfile.read(n) if n else b""
    text = data.decode("utf-8", "replace")
    if "youtube.com" not in text or "\t" not in text:
        raise HTTPError(400, "not a cookies.txt file with youtube.com cookies")
    (db.DATA / "cookies.txt").write_text(text, encoding="utf-8")
    media.forget_streams("")
    return {"ok": True}


@route("DELETE", "/api/cookies")
def del_cookies(r):
    (db.DATA / "cookies.txt").unlink(missing_ok=True)
    return {"ok": True}


@route("GET", "/api/import-old")
def import_old_status(r):
    from . import importer
    done = db.get_settings().get("imported_old")
    just = importer.STATE["done"] if done and not importer.STATE["running"] else 0
    out = {"old": None if done or importer.STATE["running"] else importer.find_old(), "imported": bool(done),
           "state": dict(importer.STATE), "just_done": just, "library": str(db.LIBRARY)}
    if just:
        importer.STATE["done"] = 0            # the "brought over" message is shown once, not on every visit
    return out


@route("POST", "/api/import-old")
def import_old(r):
    from . import importer
    return importer.start()


@route("GET", "/api/lan")
def lan_status(r):
    return lan.status()


@route("POST", "/api/lan")
def lan_switch(r):
    """Open or close the door for other devices on the Wi-Fi (an iPhone, a tablet, a computer)."""
    if HOSTED:
        raise HTTPError(400, M("hosted_disabled"))
    if r.body.get("new_code"):
        db.set_settings({"lan_code": ""})
        lan.code()
    if r.body.get("on"):
        if not lan.start(Handler):
            raise HTTPError(409, "port busy")
    elif "on" in r.body:
        lan.stop()
    db.set_settings({"lan_on": lan.status()["on"]})
    return lan.status()


@route("POST", "/api/update-downloader")
def update_downloader(r):
    if HOSTED:
        raise HTTPError(400, M("hosted_disabled"))
    if _update["running"]:
        return _update
    if APK:
        threading.Thread(target=media.update_ytdlp, args=(_update,), daemon=True).start()
        return {"running": True}
    pkgs = ["yt-dlp", "yt-dlp-ejs"] if ANDROID else ["yt-dlp[default]"]
    pkgs = ["--pre"] + pkgs                         # newest fixes for YouTube changes

    def go():
        _update.update(running=True, msg="Updating…")
        p = subprocess.run([sys.executable, "-m", "pip", "install", "-U", *pkgs], capture_output=True, text=True)
        _update.update(running=False, msg="Updated — restart Maqati to use it." if p.returncode == 0
                       else "Update failed: " + p.stderr[-200:])
    threading.Thread(target=go, daemon=True).start()
    return {"running": True}


@route("POST", "/api/open-folder")
def open_folder(r):
    if HOSTED:
        raise HTTPError(400, M("hosted_disabled"))
    p = (db.LIBRARY / (r.body.get("path") or "")).resolve()
    if p != db.LIBRARY.resolve() and db.LIBRARY.resolve() not in p.parents:
        raise HTTPError(400)
    try:
        if sys.platform == "win32":
            os.startfile(p)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}


# ---------- HTTP plumbing ----------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "Maqati"

    def log_message(self, *a):
        pass

    def do_GET(self): self.handle_any("GET")
    def do_POST(self): self.handle_any("POST")
    def do_PATCH(self): self.handle_any("PATCH")
    def do_DELETE(self): self.handle_any("DELETE")
    def do_HEAD(self): self.handle_any("GET", head=True)

    def handle_any(self, method, head=False):
        global LAST
        LAST = time.time()
        u = urlparse(self.path)
        self.query = {k: v[-1] for k, v in parse_qs(u.query).items()}
        self.body = {}
        if getattr(self.server, "maqati_lan", False):          # a request from another device on the Wi-Fi
            if u.path == "/lan-login":
                return self.lan_login(method)
            if not lan.allowed(self, u.path):
                if method == "GET" and not u.path.startswith(("/api/", "/media/", "/export", "/static/")):
                    return self.send_raw(Raw(lan.login_page().encode("utf-8"), "text/html; charset=utf-8"))
                return self.send_json({"detail": "locked"}, 401)
        try:
            for m, rx, fn in ROUTES:
                mt = rx.match(u.path)
                if m == method and mt:
                    if method not in ("GET", "DELETE") and u.path not in ("/api/upload", "/api/update/upload", "/api/cookies"):
                        n = int(self.headers.get("Content-Length") or 0)
                        raw = self.rfile.read(n) if n else b""
                        self.body = json.loads(raw) if raw.strip() else {}
                    out = fn(self, **{k: unquote(v) for k, v in mt.groupdict().items()})
                    if isinstance(out, FileOut):
                        return self.send_file(out, head)
                    if isinstance(out, Raw):
                        return self.send_raw(out)
                    return self.send_json(out)
            raise HTTPError(404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except HTTPError as e:
            self.send_json({"detail": e.msg or "error"}, e.code)
        except TypeError as e:
            if "NoneType" not in str(e):
                traceback.print_exc()
            self.send_json({"detail": "not found" if "NoneType" in str(e) else str(e)}, 404 if "NoneType" in str(e) else 500)
        except (ValueError, KeyError) as e:
            self.send_json({"detail": f"bad request: {e}"}, 400)
        except Exception as e:
            traceback.print_exc()
            try:
                self.send_json({"detail": str(e)}, 500)
            except Exception:
                pass

    def lan_login(self, method):
        if method != "POST":
            return self.send_raw(Raw(lan.login_page().encode("utf-8"), "text/html; charset=utf-8"))
        n = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(min(n, 2000)).decode("utf-8", "replace"))
        if not lan.try_login(self, (form.get("code") or [""])[0]):
            return self.send_raw(Raw(lan.login_page(wrong=True).encode("utf-8"), "text/html; charset=utf-8"))
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie", f"mq_lan={lan.token()}; Max-Age=31536000; Path=/; HttpOnly; SameSite=Lax")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_json(self, data, code=200):
        b = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def send_raw(self, o):
        self.send_response(200)
        self.send_header("Content-Type", o.ctype)
        self.send_header("Content-Length", str(len(o.data)))
        self.send_header("Cache-Control", "no-store")
        if o.download_name:
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(o.download_name)}")
        self.end_headers()
        self.wfile.write(o.data)

    def send_file(self, f, head=False):
        p = f.path
        size = p.stat().st_size
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith(("javascript", "json")):
            ctype += "; charset=utf-8"
        start, end, code = 0, size - 1, 200
        rng = self.headers.get("Range")
        m = re.match(r"bytes=(\d*)-(\d*)", rng or "")
        if m and size:
            if m[1]:
                start = int(m[1])
                end = min(int(m[2]), size - 1) if m[2] else size - 1
            elif m[2]:
                start = max(0, size - int(m[2]))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            code = 206
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if f.download:
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(p.name)}")
        self.send_header("Cache-Control", "no-cache" if f.nocache else "private, max-age=3600")
        self.end_headers()
        if head:
            return
        with open(p, "rb") as fh:
            fh.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = fh.read(min(left, 256 * 1024))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)


def open_browser(url):
    if shutil.which("termux-open-url"):
        subprocess.Popen(["termux-open-url", url])
    else:
        import webbrowser
        webbrowser.open(url)


def android_autostart():
    """On Android (Termux): start Maqati by itself when the phone turns on, and add a
    Termux shortcut that starts it and opens it. Written on every start so updates bring it."""
    if not ANDROID or APK:
        return
    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    sh = f"#!{prefix}/bin/sh\n"
    start = (f'if ! pgrep -f "python -m app.main" >/dev/null; then '
             f'MAQATI_OPEN=0 nohup {prefix}/bin/maqati >/dev/null 2>&1 & sleep 4; fi\n')
    files = {
        Path.home() / ".termux" / "boot" / "start-maqati": sh + f"{prefix}/bin/termux-wake-lock 2>/dev/null\n" + start,
        Path.home() / ".shortcuts" / "tasks" / "Maqati": sh + start + f"{prefix}/bin/termux-open-url http://localhost:8765\n",
    }
    rc = Path.home() / ".bashrc"      # older installs started Maqati in the foreground and blocked Termux
    try:
        if rc.exists():
            t = rc.read_text()
            old = 'if ! pgrep -f "python -m app.main" >/dev/null; then maqati; fi'
            if old in t:
                rc.write_text(t.replace(old, 'if ! pgrep -f "python -m app.main" >/dev/null; then (nohup maqati > "$HOME/maqati.log" 2>&1 &); '
                                            'echo "  ✅ مقاطع يعمل — Maqati is running"; fi'))
    except OSError:
        pass
    for path, text in files.items():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_text() != text:
                path.write_text(text)
            path.chmod(0o755)
        except OSError:
            pass


def main():
    host = os.environ.get("MAQATI_HOST", "127.0.0.1")
    port = int(os.environ.get("MAQATI_PORT", "8765"))
    try:
        srv = ThreadingHTTPServer((host, port), Handler)
    except OSError:
        print(f"\n  Maqati is already running. Open http://localhost:{port}\n")
        if os.environ.get("MAQATI_OPEN", "1") == "1":
            open_browser(f"http://localhost:{port}")
        return
    srv.daemon_threads = True
    android_autostart()
    media.use_updated_ytdlp()
    jobs.start()
    if db.get_settings().get("lan_on") and not HOSTED:
        lan.start(Handler)
    if APK or DESKTOP:
        media.auto_update_ytdlp(_update)
    if APK:
        import signal

        def stop(*_):
            """The app asked the engine to stop: stop ffmpeg/yt-dlp too, so none is left running alone."""
            jobs.stop_all()
            time.sleep(1)
            os._exit(0)
        signal.signal(signal.SIGTERM, stop)
    print(f"\n  Maqati is running.  Open:  http://localhost:{port}")
    if host == "0.0.0.0":
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            print(f"  On your phone (same Wi-Fi) open:  http://{s.getsockname()[0]}:{port}")
            s.close()
        except OSError:
            pass
    print(f"  Your files: {db.LIBRARY}")
    print("  Keep this window open (you can minimise it). Closing it pauses the tasks.\n")
    if os.environ.get("MAQATI_OPEN", "1") == "1":
        threading.Timer(1.0, open_browser, (f"http://localhost:{port}",)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
