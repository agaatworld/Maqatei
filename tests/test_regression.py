"""Regression test of the main features, with the real engine, real ffmpeg and a stand-in Groq.
Covers: add files (Arabic names), parts with fractions of a second, MP3 and video cuts (length checked with
ffprobe to ±0.05 s), lock/unlock, transcribe a part and a whole lesson, search with spelling variants,
notes, excerpts, projects with sections and the ZIP, book export (PDF page, Word, TXT), MP4 → MP3,
task pause/resume/cancel/clear, "My works", the Wi-Fi door.
Run:  python3 tests/test_regression.py"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
APP, GROQ = 8789, 8788
FAILS = []


def call(method, path, body=None, raw=None, ok=True):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(f"http://127.0.0.1:{APP}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
            return json.loads(b) if r.headers.get_content_type() == "application/json" else b
    except urllib.error.HTTPError as e:
        if ok:
            raise AssertionError(f"{method} {path} -> {e.code} {e.read()[:300]}")
        return e.code


def check(name, cond, info=""):
    print(("  ok  " if cond else "  FAIL ") + name + ("" if cond else f"  {info}"))
    if not cond:
        FAILS.append(name)


def wait_jobs(pred=lambda j: True, sec=240):
    end = time.time() + sec
    while time.time() < end:
        js = [j for j in call("GET", "/api/jobs") if pred(j)]
        if js and all(j["status"] in ("done", "error", "cancelled") for j in js):
            return js
        time.sleep(0.5)
    return [j for j in call("GET", "/api/jobs") if pred(j)]


def decoded(p):
    """Length by decoding every sample (does not trust the file's header)."""
    err = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", str(p), "-map", "0:a:0", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    t = [l for l in err.splitlines() if "time=" in l]
    return t[-1].split("time=")[1].split()[0] if t else "?"


FFV = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0][:60]


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout
    return float(out.strip() or 0)


def main():
    tmp = Path(tempfile.mkdtemp())
    lib = tmp / "lib"
    audio, video = tmp / "درس صوتي.mp3", tmp / "درس مرئي.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "aevalsrc=0.4*sin(2*PI*220*t)*lt(mod(t\\,4)\\,3.2):s=44100:d=95",
                    "-c:a", "libmp3lame", "-b:a", "128k", str(audio)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=25:duration=60", "-f", "lavfi",
                    "-i", "sine=frequency=330:duration=60", "-c:v", "libx264", "-g", "50", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(video)], check=True)
    env = {**os.environ, "MAQATI_DATA": str(tmp / "data"), "MAQATI_LIBRARY": str(lib), "MAQATI_OPEN": "0",
           "MAQATI_PORT": str(APP), "MAQATI_LAN_PORT": "8787", "PYTHONPATH": str(ROOT / "engine" / "vendor"),
           "MAQATI_GROQ_URL": f"http://127.0.0.1:{GROQ}/openai/v1/audio/transcriptions",
           "MAQATI_GROQ_CHAT_URL": f"http://127.0.0.1:{GROQ}/openai/v1/chat/completions",
           "MAQATI_GROQ_MODELS_URL": f"http://127.0.0.1:{GROQ}/openai/v1/models"}
    procs = [subprocess.Popen([sys.executable, str(ROOT / "tests" / "mock_groq.py"), str(GROQ)]),
             subprocess.Popen([sys.executable, "-m", "app.main"], cwd=ROOT / "engine", env=env,
                              stdout=subprocess.DEVNULL, stderr=open(tmp / "engine.log", "w"))]
    try:
        for _ in range(80):
            try:
                call("GET", "/api/health")
                break
            except Exception:
                time.sleep(0.25)
        call("POST", "/api/settings", {"groq_key": "test", "language": "ar"})
        fid = call("POST", "/api/folders", {"name": "العقيدة"})["id"]

        print("adding")
        a = call("POST", f"/api/upload?name={quote(audio.name)}&folder_id={fid}", raw=audio.read_bytes())["ids"][0]
        v = call("POST", f"/api/upload?name={quote(video.name)}", raw=video.read_bytes())["ids"][0]
        ia, iv = call("GET", f"/api/items/{a}"), call("GET", f"/api/items/{v}")
        check("audio added with its length", abs(ia["duration"] - 95) < 0.3, ia["duration"])
        check("video added as video", iv["media"] == "video" and abs(iv["duration"] - 60) < 0.3, (iv["media"], iv["duration"]))
        check("Arabic file name kept", "درس" in ia["title"], ia["title"])

        print("parts and cuts")
        ba = call("POST", f"/api/items/{a}/bookmarks", {"name": "الإخلاص", "start": 12.25, "end": 31.75})["id"]
        bv = call("POST", f"/api/items/{v}/bookmarks", {"name": "مقطع مرئي", "start": 10.4, "end": 25.6})["id"]
        call("POST", "/api/bookmarks/action", {"ids": [ba], "action": "mp3"})
        call("POST", "/api/bookmarks/action", {"ids": [bv], "action": "video"})
        call("POST", "/api/bookmarks/action", {"ids": [bv], "action": "mp3"})
        js = wait_jobs(lambda j: j["kind"] == "clip")
        check("3 cuts finished", len(js) == 3 and all(j["status"] == "done" for j in js), [(j["title"], j["status"], j["message"]) for j in js])
        for j in js:
            p = lib / (j["result"] or "")
            want = 19.5 if "الإخلاص" in j["title"] else 15.2
            d = dur(p) if p.is_file() else -1
            check(f"cut length exact ({p.suffix} {want}s)", abs(d - want) <= 0.05 if p.suffix == ".mp3" else abs(d - want) <= 0.1, d)

        print("lock")
        call("PATCH", f"/api/bookmarks/{ba}", {"done": True})
        check("locked part refuses changes", call("PATCH", f"/api/bookmarks/{ba}", {"name": "x"}, ok=False) == 423)
        call("PATCH", f"/api/bookmarks/{ba}", {"done": False})
        call("PATCH", f"/api/bookmarks/{ba}", {"name": "الإخلاص في العمل"})
        check("unlocked part can change", call("GET", f"/api/items/{a}")["bookmarks"][0]["name"] == "الإخلاص في العمل")

        print("transcription")
        call("POST", "/api/bookmarks/action", {"ids": [ba], "action": "transcribe"})
        call("POST", f"/api/items/{a}/action", {"action": "transcribe"})
        js = wait_jobs(lambda j: j["kind"] == "transcribe")
        check("part and whole lesson transcribed", len(js) == 2 and all(j["status"] == "done" for j in js), [(j["status"], j["message"]) for j in js])
        trs = call("GET", f"/api/items/{a}")["transcripts"]
        full = call("GET", f"/api/transcripts/{[t for t in trs if not t['bookmark_id']][0]['id']}")
        check("transcript has timed sentences", len(full["segments"]) > 5 and full["segments"][0]["start"] >= 0)
        txt = lib / full["file"]
        check(".txt and .srt written", txt.is_file() and txt.with_suffix(".srt").is_file())

        print("search")
        hits = call("GET", "/api/search?q=" + quote("جمله"))          # written with ه, the transcript has ة
        check("search finds spelling variants", len(hits.get("results") or []) == 1 and hits["results"][0]["hits"], str(hits)[:200])
        none = call("GET", "/api/search?q=" + quote("كلمة غير موجودة"))
        check("search with no match is empty", not none["results"])

        print("notes and excerpts")
        nid = call("POST", f"/api/items/{a}/notes", {"text": "فائدة: الإخلاص سر القبول", "time": 14})["id"]
        call("PATCH", f"/api/notes/{nid}", {"text": "فائدة معدلة"})
        xid = call("POST", f"/api/items/{a}/excerpts", {"start": 40, "end": 50, "title": "مقتطف", "text": "نص"})["id"]
        call("POST", f"/api/excerpts/{xid}/clip", {"fmt": "mp3"})
        js = wait_jobs(lambda j: j["kind"] == "clip")
        check("note and excerpt saved, excerpt cut", any("معدلة" in n["text"] for n in call("GET", f"/api/items/{a}")["notes"])
              and all(j["status"] == "done" for j in js))

        print("projects")
        pid = call("POST", "/api/projects", {"name": "مشروع الإخلاص"})["id"]
        call("POST", f"/api/projects/{pid}/clips", {"item_id": a, "start": 12.25, "end": 31.75, "title": "الأول", "section": "القسم الأول"})
        call("POST", f"/api/projects/{pid}/clips", {"item_id": v, "start": 10.4, "end": 25.6, "title": "الثاني"})
        call("POST", f"/api/projects/{pid}/export", {"fmt": "mp3"})
        js = wait_jobs(lambda j: j["kind"] == "project")
        ok = js and js[0]["status"] == "done"
        names = []
        if ok:
            z = lib / js[0]["result"]
            with zipfile.ZipFile(z) as zz:
                names = zz.namelist()
        check("project ZIP with numbered clips, sub-folder and Word book", ok and any("القسم الأول" in n for n in names)
              and any(n.endswith(".docx") for n in names) and sum(n.endswith(".mp3") for n in names) == 2, (js and js[0]["message"], names))

        print("book export")
        html = call("GET", f"/export?src=item&id={a}&which=full&fmt=html")
        check("PDF page renders", b"<html" in html and "جملة".encode() in html)
        docx = call("GET", f"/export?src=item&id={a}&which=full&fmt=docx")
        check("Word file is a real .docx", docx[:2] == b"PK" and b"word/document.xml" in docx)
        txt = call("GET", f"/export?src=item&id={a}&which=clips&fmt=txt")
        check("TXT export", len(txt) > 10)

        print("lesson map")
        call("POST", f"/api/items/{a}/action", {"action": "map"})
        js = wait_jobs(lambda j: j["kind"] == "map")
        mp = call("GET", f"/api/items/{a}")["map"] or {}
        ch = mp.get("chapters") or []
        check("map made with ordered chapters that cover the lesson", js and js[0]["status"] == "done" and len(ch) >= 2
              and all(ch[k]["t"] < ch[k + 1]["t"] and ch[k]["end"] == ch[k + 1]["t"] for k in range(len(ch) - 1))
              and ch[0]["t"] <= 1 and "summary" not in mp, (js and js[0]["message"], ch[:3]))
        check("map needs a transcript", call("POST", f"/api/items/{v}/action", {"action": "map"}, ok=False) == 400)

        print("silences")
        fa = call("GET", f"/api/items/{a}")["file"]          # the test lesson: 3.2 s of sound, then 0.8 s of silence
        first = call("GET", "/api/silence?path=" + quote(fa))
        wait_jobs(lambda j: j["kind"] == "levels")
        sil = call("GET", "/api/silence?path=" + quote(fa))
        sp = sil.get("spans") or []
        check("silences found for listening", first.get("pending") and 20 <= len(sp) <= 24
              and all(0.4 < b - a_ < 0.8 for a_, b in sp), (first, len(sp), sp[:3]))
        check("a margin is kept around the words", all(abs(((a_ - 3.2) % 4)) < 0.3 for a_, b in sp), sp[:4])
        check("longer minimum skips nothing here", call("GET", "/api/silence?min=1&path=" + quote(fa))["spans"] == [])
        call("POST", "/api/nosil", {"path": fa})
        call("POST", "/api/nosil", {"path": iv["file"]})
        js = wait_jobs(lambda j: j["kind"] == "nosil")
        ja = [j for j in js if j["item_id"] == a]
        got = dur(lib / ja[0]["result"]) if ja and ja[0]["status"] == "done" else -1
        check("copy without silences is shorter by exactly the skipped time", abs(got - (95 - sil["saved"])) < 0.15,
              (got, sil["saved"], ja and ja[0]["message"], ja and ja[0]["result"] and decoded(lib / ja[0]["result"]), FFV))
        jv = [j for j in js if j["item_id"] == v]
        check("video with no silences says so", jv and jv[0]["status"] == "done" and not jv[0]["result"] and "سكتات" in jv[0]["message"], jv and (jv[0]["status"], jv[0]["message"]))
        call("POST", "/api/bookmarks/action", {"ids": [ba], "action": "mp3", "nosil": True})
        js = wait_jobs(lambda j: j["kind"] == "clip" and "بدون" in j["title"])
        got = dur(lib / js[0]["result"]) if js and js[0]["status"] == "done" else -1
        check("a part made without silences", js and 15 < got < 18.5 and "بدون سكتات" in js[0]["result"], (got, js and js[0]["message"]))

        call("POST", "/api/bookmarks/action", {"ids": [bv], "action": "video", "nosil": True})
        js = wait_jobs(lambda j: j["kind"] == "clip" and "بدون" in j["title"] and j["item_id"] == v)
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                              str(lib / (js[0]["result"] or "x"))], capture_output=True, text=True).stdout if js and js[0]["status"] == "done" else ""
        check("a video part without silences stays a video", "video" in out and js[0]["result"].endswith(".mp4") and "بدون سكتات" in js[0]["result"],
              (out, js and js[0]["result"], js and js[0]["message"]))

        print("convert and tasks")
        call("POST", f"/api/items/{v}/action", {"action": "convert"})
        js = wait_jobs(lambda j: j["kind"] == "convert")
        check("MP4 to MP3", js and js[0]["status"] == "done" and abs(dur(lib / js[0]["result"]) - 60) < 0.3, js and js[0]["message"])
        call("POST", f"/api/items/{v}/action", {"action": "transcribe"})
        tj = [j for j in call("GET", "/api/jobs") if j["kind"] == "transcribe" and j["item_id"] == v][0]
        call("POST", f"/api/jobs/{tj['id']}/pause")
        time.sleep(1)
        st = [j for j in call("GET", "/api/jobs") if j["id"] == tj["id"]][0]["status"]
        call("POST", f"/api/jobs/{tj['id']}/resume")
        js = wait_jobs(lambda j: j["id"] == tj["id"])
        check("pause then resume finishes", st == "paused" and js[0]["status"] == "done", (st, js[0]["status"]))
        call("POST", f"/api/items/{v}/action", {"action": "convert"})
        cj = max(j["id"] for j in call("GET", "/api/jobs") if j["kind"] == "convert")
        call("POST", f"/api/jobs/{cj}/cancel")
        check("cancel", [j for j in call("GET", "/api/jobs") if j["id"] == cj][0]["status"] == "cancelled")
        before = len(call("GET", f"/api/folders/all/contents")["works"])
        call("POST", "/api/jobs-clear")
        after = call("GET", "/api/folders/all/contents")["works"]
        check("clearing finished tasks keeps My works", len(after) == before and before >= 4, (before, len(after)))

        print("wi-fi door")
        st = call("POST", "/api/lan", {"on": True})
        code = urllib.request.urlopen("http://127.0.0.1:8787/").read()
        check("Wi-Fi door asks for the code", st["on"] and b"lan-login" in code)
        call("POST", "/api/lan", {"on": False})
        if os.environ.get("KEEP"):                       # leave the engine running for the screen walk-through
            print("READY", flush=True)
            time.sleep(int(os.environ["KEEP"]))
    finally:
        for p in procs:
            p.terminate()
        log = (tmp / "engine.log").read_text()
        if "Traceback" in log:
            print("engine log has errors:\n" + log[-3000:])
    print("\n" + ("ALL OK" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}"))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
