"""The Maqati engine inside a web page (the iPhone version), run by Pyodide.

The page's code (web/boot.js) calls dispatch() for every /api/… request and step() to run tasks. Everything is
the normal engine (routes, database, export, search, the task runners). Only two things are different:
- ffmpeg and the transcription service cannot be called from here. When the engine needs one of them, step()
  stops with {"need": …}; the page does that work (ffmpeg.wasm, or fetch to Groq), hands the answer back with
  provide(), and step() runs the task again from the top. Finished pieces are kept on disk, so a task goes
  forward a little more each time until it is done.
- files live in the browser's own storage (IndexedDB), saved by the page after every change."""
import io
import json
import mimetypes
import os
import threading
import traceback
import sys
import types
from urllib.parse import parse_qs, unquote, urlparse

if "requests" not in sys.modules:              # the real one needs sockets; the page makes web calls instead
    sys.modules["requests"] = types.SimpleNamespace(RequestException=Exception)

from . import db, jobs, main, media, mirrors, transcribe

MEMO = {}                 # answers the page gave back: key -> result
_DONE = {}                # finished downloads of the running task
_probe = {}               # length and kind of a file being added (the page measures it before sending it)


class NeedJS(BaseException):
    """Not an error: the page must do something (run ffmpeg, call a web service) and then try again."""

    def __init__(self, kind, payload):
        super().__init__(kind)
        self.kind, self.payload = kind, payload


def _key(*parts):
    import hashlib
    return hashlib.sha1(json.dumps(parts, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


# ---------- ffmpeg, done by the page ----------
class _Done:
    def __init__(self, code, log):
        self.returncode, self.stdout, self.stderr = code, log, log


def _ffmpeg(cmd):
    cmd = [str(c) for c in cmd]
    k = _key("ff", cmd)
    if k not in MEMO:
        raise NeedJS("ffmpeg", {"key": k, "cmd": cmd})
    return MEMO[k]


# yt-dlp cannot run in a browser. Its calls "fail" with the message the engine treats as YouTube blocking it,
# so the engine goes straight to its free YouTube mirrors (which a browser can reach).
NO_YTDLP = "ERROR: Sign in to confirm you're not a bot (no yt-dlp in the browser)"
_is_ffmpeg = lambda cmd: str(cmd[0]).endswith("ffmpeg")


class _Subprocess:
    """Stands in for the subprocess module inside media.py."""
    PIPE = STDOUT = DEVNULL = None

    class CompletedProcess(_Done):
        pass

    @staticmethod
    def run(cmd, **kw):
        code, log = _ffmpeg(cmd) if _is_ffmpeg(cmd) else (1, NO_YTDLP)
        return _Done(code, log)

    class Popen:
        def __init__(self, cmd, **kw):
            self.returncode, log = _ffmpeg(cmd) if _is_ffmpeg(cmd) else (1, NO_YTDLP)
            self.stdout = io.StringIO(log)

        def wait(self, timeout=None):
            return self.returncode

        def poll(self):
            return self.returncode

        def kill(self):
            pass


class _NoThread:
    """There are no threads in a web page: the watchdogs are not needed there."""

    def __init__(self, target=None, args=(), kwargs=None, daemon=None, name=None):
        pass

    def start(self):
        pass


class _Threading:
    Thread = _NoThread
    Event = threading.Event
    Lock = threading.Lock
    RLock = threading.RLock
    Timer = _NoThread


class _Executor:
    """A ThreadPoolExecutor that simply runs each piece of work when it is submitted."""

    def __init__(self, *a, **kw):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def submit(self, fn, *a, **kw):
        import concurrent.futures
        f = concurrent.futures.Future()
        try:
            f.set_result(fn(*a, **kw))
        except BaseException as e:
            f.set_exception(e)
        return f

    def map(self, fn, it):
        return [fn(x) for x in it]

    def shutdown(self, *a, **kw):
        pass


# ---------- the transcription service, called by the page ----------
class _Resp:
    def __init__(self, status, text, headers):
        self.status_code, self.text, self.headers = status, text, headers or {}

    def json(self):
        return json.loads(self.text)


class _Requests:
    class RequestException(Exception):
        pass

    @staticmethod
    def post(url, headers=None, files=None, data=None, json=None, timeout=None):
        name, fobj, mime = files["file"] if files else (None, None, None)
        path = getattr(fobj, "name", None)
        items = list(data.items()) if isinstance(data, dict) else list(data or [])
        return _Requests._ask("POST", url, headers, items, path, name, mime, json)

    @staticmethod
    def get(url, headers=None, timeout=None, **kw):
        return _Requests._ask("GET", url, headers, [], None, None, None, None)

    @staticmethod
    def plan(method, url, headers=None, body=None):
        """What the page must fetch for a request the engine will make later (see prefetch)."""
        k = _key("http", method, url, None, 0, [], body)
        return {"key": k, "method": method, "url": url, "headers": headers or {}, "data": [], "file": None, "name": None,
                "mime": None, "json": body}

    @staticmethod
    def _ask(method, url, headers, items, path, name, mime, body):
        k = _key("http", method, url, path, os.path.getsize(path) if path else 0, items, body)
        if k not in MEMO:
            raise NeedJS("http", {"key": k, "method": method, "url": url, "headers": headers or {}, "data": items,
                                  "file": path, "name": name, "mime": mime, "json": body})
        # the transcription service: a success is kept (the task runs again from the top), anything else is used
        # once so the engine's own retry loop asks again. Other answers (the YouTube mirrors) are final either way.
        st, text, hd = MEMO[k] if MEMO[k][0] == 200 or "groq.com" not in url else MEMO.pop(k)
        if st == 0:
            raise _Requests.RequestException(text)
        return _Resp(st, text, hd)


def _plan(kind, base, vid):
    """The request mirrors._one(kind, base, vid) will make, in the page's terms."""
    if kind == "cobalt":
        return _Requests.plan("POST", base.rstrip("/") + "/", {"Accept": "application/json", "Content-Type": "application/json"},
                              {"url": f"https://www.youtube.com/watch?v={vid}", "videoQuality": "720", "youtubeVideoCodec": "h264"})
    if kind == "piped":
        return _Requests.plan("GET", f"{base}/streams/{vid}")
    return _Requests.plan("GET", f"{base}/api/v1/videos/{vid}?local=true")


def _lookup(vid, _real=mirrors.lookup):
    """Ask every mirror at once: the page fetches them all in parallel, then the engine's own lookup reads the answers."""
    plans = [_plan(k, b, vid) for k, b in mirrors.servers()]
    todo = [p for p in plans if p["key"] not in MEMO]
    if todo:
        raise NeedJS("http_many", {"reqs": todo})
    return _real(vid)


def _setup():
    sys.modules["requests"] = _Requests
    media.subprocess = _Subprocess
    media.threading = _Threading
    jobs.ThreadPoolExecutor = _Executor
    mirrors.requests = _Requests
    mirrors.ThreadPoolExecutor = _Executor
    mirrors.lookup = _lookup
    transcribe.requests = _Requests
    transcribe._sleep = lambda *a, **kw: None     # the page itself waits before asking the service again
    real_probe = media.probe

    def probe(path):
        if _probe:                                 # a file just added: the page measured it already
            return _probe["dur"], _probe["kind"]
        return real_probe(path)
    media.probe = probe
    real_dl = media.ytdlp_download

    def ytdlp_download(url, out_template, want, height, cancel=None, progress=None, section=None):
        """A finished download is remembered: the task runs again from the top, but the file moved only once."""
        k = ("dl", url, str(out_template), want, height, section)
        got = _DONE.get(k)
        if got and got.exists():
            return got
        got = real_dl(url, out_template, want, height, cancel, progress, section)
        _DONE[k] = got
        return got
    media.ytdlp_download = ytdlp_download
    real_work = jobs.work

    def work(jid, fresh=False):              # a task runs again from the top: keep what ffmpeg already made
        return real_work(jid, False)
    jobs.work = work


_setup()


def provide(key, result_json):
    """The page's answer to a {"need": …}: ffmpeg -> [exit code, log]; http -> [status, text, headers]."""
    MEMO[key] = tuple(json.loads(result_json))


# ---------- requests from the page ----------
class _Req:
    pass


class _Headers(dict):
    def get(self, k, d=None):
        for kk, v in self.items():
            if kk.lower() == k.lower():
                return v
        return d


RAW_PATHS = ("/api/upload", "/api/update/upload", "/api/cookies")
ONLY_YT = "في نسخة الويب تعمل روابط يوتيوب فقط. لمواقع أخرى استخدم تطبيق الأندرويد أو الكمبيوتر، أو أضف الدرس كملف. / On the web version only YouTube links work; for other sites use the Android or desktop app, or add the lesson as a file."
OFF_HERE = {"/api/update-downloader": "", "/api/lan": "", "/api/import-old": "", "/api/open-folder": "",
            "/api/test-mirrors": "", "/api/cookies": ""}


def dispatch(method, url, body=b"", dur=None, kind=None):
    """One /api/… or /export request. Returns [status, content type, body bytes, download name]."""
    u = urlparse(url)
    r = _Req()
    r.query = {k: v[-1] for k, v in parse_qs(u.query).items()}
    body = body.to_bytes() if hasattr(body, "to_bytes") else bytes(body or b"")   # from the page: a Uint8Array
    r.headers = _Headers({"Content-Length": str(len(body))})
    r.rfile = io.BytesIO(body)
    r.body = {}
    if u.path in OFF_HERE and (method != "GET" or OFF_HERE[u.path]):
        return [400, "application/json", json.dumps({"detail": OFF_HERE[u.path] or "not on iPhone"}).encode(), None]
    try:
        for m, rx, fn in main.ROUTES:
            mt = rx.match(u.path)
            if m == method and mt:
                if method not in ("GET", "DELETE") and u.path not in RAW_PATHS:
                    r.body = json.loads(body) if body.strip() else {}
                if u.path == "/api/links":
                    urls = [x for x in (r.body.get("text") or "").split() if x.startswith(("http://", "https://"))]
                    if any(not media.is_youtube(x) for x in urls):
                        raise main.HTTPError(400, ONLY_YT)
                if u.path == "/api/upload":
                    _probe.update(dur=float(dur or 0), kind=kind or "audio")
                try:
                    out = fn(r, **{k: unquote(v) for k, v in mt.groupdict().items()})
                finally:
                    _probe.clear()
                if u.path == "/api/health":
                    out = dict(out, web=True, apk=False, android=False, ffmpeg=True, js=None, ytdlp=None)
                if isinstance(out, main.Raw):
                    return [200, out.ctype, out.data, out.download_name]
                if isinstance(out, main.FileOut):
                    ct = mimetypes.guess_type(out.path.name)[0] or "application/octet-stream"
                    return [200, ct, out.path.read_bytes(), out.path.name if out.download else None]
                return [200, "application/json", json.dumps(out, ensure_ascii=False).encode("utf-8"), None]
        raise main.HTTPError(404)
    except main.HTTPError as e:
        return [e.code, "application/json", json.dumps({"detail": e.msg or "error"}).encode(), None]
    except TypeError as e:                      # same answers as the normal engine (main.Handler)
        if "NoneType" in str(e):
            return [404, "application/json", b'{"detail": "not found"}', None]
        traceback.print_exc()
        return [500, "application/json", json.dumps({"detail": str(e)}).encode(), None]
    except (ValueError, KeyError) as e:
        return [400, "application/json", json.dumps({"detail": f"bad request: {e}"}).encode(), None]
    except NeedJS as n:                         # the page does it, then asks again (only reading routes need this)
        return [0, "need", json.dumps(dict(n.payload, need=n.kind)).encode(), None]
    except Exception as e:
        traceback.print_exc()
        return [500, "application/json", json.dumps({"detail": str(e)}).encode(), None]


# ---------- tasks ----------
SUPPORTED = ("clip", "convert", "transcribe", "project", "info", "fetch")


def next_job():
    """Start the oldest waiting task (one at a time on a phone). Returns its id or None."""
    run = db.one("SELECT id FROM jobs WHERE status='running'")
    if run:
        return run["id"]
    for j in db.q("SELECT * FROM jobs WHERE status='queued' ORDER BY id"):
        if j["kind"] not in SUPPORTED:
            jobs.set_job(j["id"], status="error", message=ONLY_YT)
            continue
        jobs.set_job(j["id"], status="running", message="…")
        return j["id"]
    return None


def step(jid):
    """Run a task as far as it can go. Returns {"done"}, {"stop"}, {"error"} or {"need": …}."""
    job = db.one("SELECT * FROM jobs WHERE id=?", (int(jid),))
    if not job or job["status"] != "running":
        return json.dumps({"stop": job["status"] if job else "gone"})
    ev = threading.Event()
    with jobs._lock:
        jobs._running[job["id"]] = ev
    try:
        jobs._run(job, ev)
    except NeedJS as n:
        return json.dumps(dict(n.payload, need=n.kind))
    cur = db.one("SELECT status, result, message FROM jobs WHERE id=?", (job["id"],))
    if cur and cur["status"] == "done":
        MEMO.clear(); _DONE.clear()
        return json.dumps({"done": cur["result"]})
    if cur and cur["status"] == "error":
        MEMO.clear(); _DONE.clear()
        return json.dumps({"error": cur["message"]})
    return json.dumps({"stop": cur["status"] if cur else "gone"})


def status(jid):
    """A task's state, so the page can stop ffmpeg or a wait when the task was paused or cancelled."""
    j = db.one("SELECT status FROM jobs WHERE id=?", (int(jid),))
    return j["status"] if j else "gone"


def progress(jid, p, msg=None):
    """Progress of a download the page is doing for a task (0..1)."""
    j = db.one("SELECT status FROM jobs WHERE id=?", (int(jid),))
    if j and j["status"] == "running":
        jobs.set_job(int(jid), progress=round(max(0.0, min(1.0, float(p))), 4), **({"message": msg} if msg else {}))
