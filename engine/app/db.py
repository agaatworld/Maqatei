"""SQLite storage. Everything the app knows lives in data/maqati.db."""
import json
import sqlite3
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import os
DATA = Path(os.environ.get("MAQATI_DATA") or ROOT / "data")           # database, cookies, temp work
LIBRARY = Path(os.environ.get("MAQATI_LIBRARY") or ROOT / "library")  # your media, parts, transcripts
WORK = DATA / "work"                # temporary pieces (safe to delete when nothing is running)
for d in (DATA, LIBRARY, WORK):
    d.mkdir(parents=True, exist_ok=True)

_lock = threading.RLock()
_conn = sqlite3.connect(DATA / "maqati.db", check_same_thread=False)
_conn.row_factory = sqlite3.Row
# in the iPhone version the database file is kept in the browser's storage, which needs a single file
_conn.execute("PRAGMA journal_mode=" + ("DELETE" if os.environ.get("MAQATI_WEB") == "1" else "WAL"))

_conn.executescript("""
CREATE TABLE IF NOT EXISTS folders (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, created REAL);
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY, folder_id INTEGER, title TEXT, kind TEXT, url TEXT,
  file TEXT, media TEXT, duration REAL, dir TEXT, thumb TEXT, created REAL);
CREATE TABLE IF NOT EXISTS bookmarks (
  id INTEGER PRIMARY KEY, item_id INTEGER, name TEXT, start REAL, end REAL, created REAL);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY, kind TEXT, item_id INTEGER, bookmark_id INTEGER, title TEXT,
  params TEXT, status TEXT, progress REAL, message TEXT, result TEXT,
  created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS transcripts (
  id INTEGER PRIMARY KEY, item_id INTEGER, bookmark_id INTEGER, title TEXT,
  start REAL, end REAL, text TEXT, segments TEXT, engine TEXT, file TEXT, created REAL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY, item_id INTEGER, text TEXT, time REAL, created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY, name TEXT, description TEXT, created REAL);
CREATE TABLE IF NOT EXISTS project_clips (
  id INTEGER PRIMARY KEY, project_id INTEGER, item_id INTEGER, start REAL, end REAL,
  title TEXT, note TEXT, pos REAL, created REAL);
CREATE TABLE IF NOT EXISTS project_items (
  project_id INTEGER, item_id INTEGER, created REAL, PRIMARY KEY (project_id, item_id));
CREATE TABLE IF NOT EXISTS paras (scope TEXT PRIMARY KEY, data TEXT);
CREATE TABLE IF NOT EXISTS excerpts (
  id INTEGER PRIMARY KEY, item_id INTEGER, start REAL, end REAL, title TEXT, text TEXT, note TEXT, created REAL);
""")
# upgrades for databases made by older versions
for table, col, typ in [("folders", "color", "TEXT"), ("folders", "icon", "TEXT"),
                        ("items", "note", "TEXT"), ("bookmarks", "note", "TEXT"),
                        ("jobs", "elapsed", "REAL"), ("jobs", "run_start", "REAL"), ("jobs", "media", "REAL"),
                        ("jobs", "speed_key", "TEXT"), ("jobs", "taken", "REAL"),
                        ("project_clips", "section", "TEXT"), ("projects", "sections", "TEXT"),
                        ("bookmarks", "done", "INTEGER"), ("items", "pinned", "REAL"),
                        ("items", "heights", "TEXT"), ("jobs", "hidden", "INTEGER")]:
    if col not in [r[1] for r in _conn.execute(f"PRAGMA table_info({table})")]:
        _conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
_conn.commit()

DEFAULT_SETTINGS = {
    "engine": "groq",                 # groq | local
    "groq_key": "",
    "groq_model": "whisper-large-v3",  # most accurate; whisper-large-v3-turbo is a bit faster
    "local_model": "large-v3-turbo",
    "language": "ar",
    "prompt": "",
    "max_downloads": 3,
    "max_transcribes": 2,
    "video_height": 720,
    "lang": "ar",
    "auto_download": "video",   # what to do with a new link: video | audio | none
    "theme": "auto",        # auto | light | dark | sepia
    "accent": "#0F5C4D",
    "font_scale": 1.0,
    "show_transcript": True,
    "follow": True,
    "pad_before": 3,        # seconds added before a search hit when making a clip
    "pad_after": 5,
    "font_ui": "almarai",   # the app's text
    "font_head": "almarai", # headings
    "font_read": "amiri",   # transcripts and reading
    "reencode_video": False, # video parts: False = instant copy with exact start/end marks; True = re-encode
    "dhikr": 15,            # minutes between the small reminder (0 = off)
    "reminders": True,      # the small banner of verses and hadiths
    "imported_old": None,   # when the lessons of the old (Termux) version were brought over
    "lan_on": False,        # open from an iPhone or another device on the same Wi-Fi
    "lan_code": "",         # the 6-digit code that device must type once
}


def q(sql, args=()):
    with _lock:
        return [dict(r) for r in _conn.execute(sql, args).fetchall()]


def one(sql, args=()):
    r = q(sql, args)
    return r[0] if r else None


def run(sql, args=()):
    with _lock:
        cur = _conn.execute(sql, args)
        _conn.commit()
        return cur.lastrowid


def now():
    return time.time()


def get_settings():
    s = dict(DEFAULT_SETTINGS)
    for r in q("SELECT key, value FROM settings"):
        try:
            s[r["key"]] = json.loads(r["value"])
        except Exception:
            s[r["key"]] = r["value"]
    return s


def set_settings(d):
    for k, v in d.items():
        if k in DEFAULT_SETTINGS:
            run("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, json.dumps(v)))
