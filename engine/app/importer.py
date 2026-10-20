"""Bring everything over from the old Maqati (3.x, run by Termux on the same phone) while it is running.

The old version keeps its database inside Termux, where this app cannot read it. But it serves the same
web API at 127.0.0.1:8765, so its lessons, parts, transcripts, notes, excerpts, finished cuts and projects
are read from there and written here. The media files themselves stay where they are (the phone's Maqati
folder is shared by both versions)."""
import json
import threading
import urllib.request

from . import db

OLD = "http://127.0.0.1:8765"
STATE = {"running": False, "done": 0, "total": 0, "msg": "", "error": None}


def _get(path, timeout=20):
    with urllib.request.urlopen(OLD + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def find_old():
    """Is the old version running? Returns its version and how many lessons it has, or None."""
    try:
        h = _get("/api/health", 3)
    except Exception:
        return None
    if h.get("apk"):                       # that is this app, not the old one
        return None
    try:
        n = len(_get("/api/state", 10).get("items") or [])
    except Exception:
        n = None
    return {"version": h.get("version"), "items": n, "library": h.get("library")}


def _ins(table, row, cols):
    keys = [c for c in cols if c in row]
    return db.run(f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))})",
                  tuple(row[k] for k in keys))


def run():
    """Copy everything. Safe to run once; a second run is refused (it would duplicate the lessons)."""
    if STATE["running"]:
        return
    STATE.update(running=True, done=0, total=0, msg="", error=None)
    try:
        st = _get("/api/state", 30)
        items = sorted(st.get("items") or [], key=lambda i: i["id"])
        STATE["total"] = len(items)
        fmap, imap, bmap = {}, {}, {}
        for f in st.get("folders") or []:
            fmap[f["id"]] = _ins("folders", f, ("name", "created", "color", "icon"))
        for summary in items:
            d = _get(f"/api/items/{summary['id']}", 30)
            d["folder_id"] = fmap.get(d.get("folder_id"))
            iid = _ins("items", d, ("folder_id", "title", "kind", "url", "file", "media", "duration", "dir", "thumb",
                                    "created", "note", "pinned", "heights"))
            imap[d["id"]] = iid
            for b in d.get("bookmarks") or []:
                b["item_id"] = iid
                bmap[b["id"]] = _ins("bookmarks", b, ("item_id", "name", "start", "end", "created", "note", "done"))
            for t in d.get("transcripts") or []:
                full = _get(f"/api/transcripts/{t['id']}", 30)
                full["item_id"], full["bookmark_id"] = iid, bmap.get(full.get("bookmark_id"))
                full["segments"] = json.dumps(full.get("segments") or [], ensure_ascii=False)
                _ins("transcripts", full, ("item_id", "bookmark_id", "title", "start", "end", "text", "segments", "engine",
                                           "file", "created"))
            for n in d.get("notes") or []:
                n["item_id"] = iid
                _ins("notes", n, ("item_id", "text", "time", "created", "updated"))
            for x in d.get("excerpts") or []:
                x["item_id"] = iid
                _ins("excerpts", x, ("item_id", "start", "end", "title", "text", "note", "created"))
            for j in d.get("jobs") or []:           # finished cuts and downloads, so they show in "My works"
                if j.get("status") != "done" or j.get("kind") not in ("clip", "fetch", "convert", "transcribe"):
                    continue
                j.update(item_id=iid, bookmark_id=bmap.get(j.get("bookmark_id")), status="done", progress=1,
                         params=json.dumps(j.get("params") or {}, ensure_ascii=False), hidden=0)
                j.setdefault("created", db.now())
                _ins("jobs", j, ("kind", "item_id", "bookmark_id", "title", "params", "status", "progress", "message",
                                 "result", "created", "taken", "hidden"))
            STATE["done"] += 1
            STATE["msg"] = summary.get("title") or ""
        for p in sorted(_get("/api/projects", 30), key=lambda p: p["id"]):
            full = _get(f"/api/projects/{p['id']}", 60)
            full["sections"] = json.dumps(full.get("sections") or [], ensure_ascii=False)
            pid = _ins("projects", full, ("name", "description", "created", "sections"))
            for c in full.get("clips") or []:
                if c.get("item_id") in imap:
                    c.update(project_id=pid, item_id=imap[c["item_id"]])
                    _ins("project_clips", c, ("project_id", "item_id", "start", "end", "title", "note", "pos", "created",
                                              "section"))
            for it in full.get("items") or []:
                if it["id"] in imap:
                    db.run("INSERT OR IGNORE INTO project_items (project_id, item_id, created) VALUES (?,?,?)",
                           (pid, imap[it["id"]], db.now()))
        db.set_settings({"imported_old": db.now()})
    except Exception as e:
        STATE["error"] = str(e)[:300]
    finally:
        STATE["running"] = False


def start():
    if db.get_settings().get("imported_old"):
        return {"error": "already"}
    threading.Thread(target=run, daemon=True).start()
    return {"started": True}
