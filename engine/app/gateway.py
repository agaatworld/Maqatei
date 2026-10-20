"""The multi-user front door for a hosted Maqati (used only when you deploy it online for several
people to share one link). Each visitor registers a username + password and gets a completely
private copy of the app: its own database and its own media folder, running as its own isolated
`python -m app.main` process on a local-only port. This file never touches anyone's data itself —
it only signs people in and forwards their traffic to their own private process. Everyday local /
phone use (python -m app.main directly) never runs this file and is completely unaffected by it.

Start with:  python -m app.gateway
Needs, as environment variables:
  PORT             the port to listen on (hosts like Render set this for you; default 8080)
  MAQATI_ROOT      where accounts + everyone's files are kept (default: ./data-root next to this app)
  MAQATI_INVITE    optional — if set, new accounts must type this code to register
  MAQATI_HTTPS     set to 1 if you are always served over https (marks the login cookie Secure)
"""
import hashlib
import html
import http.client
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent          # the "maqati" folder (contains the app/ package)
DATA_ROOT = Path(os.environ.get("MAQATI_ROOT") or ROOT / "data-root")   # put this on a persistent disk when hosting
USERS_DIR = DATA_ROOT / "users"
INVITE = (os.environ.get("MAQATI_INVITE") or "").strip()
FORCE_HTTPS = os.environ.get("MAQATI_HTTPS") == "1"
IDLE_LIMIT = 30 * 60             # stop a person's process after this long with no requests (frees memory)
REAP_EVERY = 60
COOKIE = "mqs"
DATA_ROOT.mkdir(parents=True, exist_ok=True)
USERS_DIR.mkdir(parents=True, exist_ok=True)

# ---------- accounts: one small shared database of who's who (never anyone's media/transcripts) ----------
_lock = threading.RLock()
_auth = sqlite3.connect(DATA_ROOT / "gateway.db", check_same_thread=False)
_auth.row_factory = sqlite3.Row
_auth.execute("PRAGMA journal_mode=WAL")
_auth.executescript("""
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
  salt TEXT, hash TEXT, created REAL);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, created REAL);
""")
_auth.commit()


def _pwhash(password, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000).hex()


def _username_ok(u):
    u = (u or "").strip()
    return 2 <= len(u) <= 30 and all(c.isalnum() or c in " ._-" for c in u)


def create_user(username, password):
    username = username.strip()
    if not _username_ok(username):
        raise ValueError("bad_name")
    if len(password) < 4:
        raise ValueError("short_pw")
    salt = secrets.token_hex(16)
    with _lock:
        if _auth.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone():
            raise ValueError("taken")
        cur = _auth.execute("INSERT INTO users (username, salt, hash, created) VALUES (?,?,?,?)",
                            (username, salt, _pwhash(password, salt), time.time()))
        _auth.commit()
        return cur.lastrowid


def verify_user(username, password):
    with _lock:
        r = _auth.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", ((username or "").strip(),)).fetchone()
    if not r or not secrets.compare_digest(_pwhash(password, r["salt"]), r["hash"]):
        return None
    return r["id"], r["username"]


def new_session(uid):
    tok = secrets.token_urlsafe(32)
    with _lock:
        _auth.execute("INSERT INTO sessions (token, user_id, created) VALUES (?,?,?)", (tok, uid, time.time()))
        _auth.commit()
    return tok


def session_user(token):
    if not token:
        return None
    with _lock:
        r = _auth.execute("SELECT u.id, u.username FROM sessions s JOIN users u ON u.id=s.user_id "
                          "WHERE s.token=?", (token,)).fetchone()
    return (r["id"], r["username"]) if r else None


def end_session(token):
    with _lock:
        _auth.execute("DELETE FROM sessions WHERE token=?", (token,))
        _auth.commit()


# ---------- one private backend process per person ----------
_procs = {}       # user id -> {"proc", "port", "last", "username"}
_procs_lock = threading.RLock()


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_ready(port, budget=12.0):
    t0 = time.time()
    while time.time() - t0 < budget:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def ensure_backend(uid, username):
    with _procs_lock:
        info = _procs.get(uid)
        if info and info["proc"].poll() is None:
            info["last"] = time.time()
            return info["port"]
        port = _free_port()
        udir = USERS_DIR / str(uid)
        env = {**os.environ, "MAQATI_HOST": "127.0.0.1", "MAQATI_PORT": str(port), "MAQATI_OPEN": "0",
              "MAQATI_HOSTED": "1", "MAQATI_DATA": str(udir / "data"), "MAQATI_LIBRARY": str(udir / "library"),
              "MAQATI_USERNAME": username}
        proc = subprocess.Popen([sys.executable, "-m", "app.main"], cwd=str(ROOT), env=env)
        _procs[uid] = {"proc": proc, "port": port, "last": time.time(), "username": username}
    if not _wait_ready(port):
        raise RuntimeError("backend did not start")
    return port


def _reap():
    while True:
        time.sleep(REAP_EVERY)
        now = time.time()
        with _procs_lock:
            for uid, info in list(_procs.items()):
                if info["proc"].poll() is not None:
                    del _procs[uid]
                elif now - info["last"] > IDLE_LIMIT:
                    try:
                        info["proc"].terminate()
                    except Exception:
                        pass
                    del _procs[uid]


# ---------- the sign-in page (plain HTML + CSS, no JS needed) ----------
ERRS = {"bad_name": "اسم المستخدم غير صالح (حرفان إلى ٣٠ حرفًا، بدون رموز غريبة).",
       "short_pw": "كلمة السر قصيرة — أربعة أحرف على الأقل.",
       "taken": "اسم المستخدم هذا محجوز، جرّب اسمًا آخر.",
       "wrong": "اسم المستخدم أو كلمة السر غير صحيحة.",
       "invite": "رمز الدعوة غير صحيح.",
       "start": "تعذّر تجهيز مساحتك الآن، أعد المحاولة بعد لحظات."}


def login_page(err=None, tab="1"):
    tab = "2" if tab == "2" else "1"
    err_html = f'<p class="err">{html.escape(ERRS.get(err, err or ""))}</p>' if err else ""
    invite_field = ('<input type="text" name="inv" placeholder="رمز الدعوة" required>' if INVITE else "")
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>مقاطع</title>
<style>
:root{{color-scheme:light dark}}
*{{box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Arial,sans-serif;background:#eef5f3;display:flex;min-height:100vh;
  align-items:center;justify-content:center;margin:0;padding:20px;color:#1a2320}}
.card{{background:#fff;max-width:380px;width:100%;border-radius:18px;padding:30px 26px;box-shadow:0 10px 40px rgba(0,0,0,.12)}}
@media (prefers-color-scheme: dark){{body{{background:#0b1512;color:#e9efec}}
  .card{{background:#141d1a;box-shadow:0 10px 40px rgba(0,0,0,.4)}}
  input{{background:#0e1613 !important;color:#eee !important;border-color:#2a3733 !important}}}}
h1{{margin:0 0 2px;font-size:1.5rem;text-align:center}}
p.sub{{text-align:center;color:#6b8f84;margin:2px 0 20px;font-size:.9rem}}
.tabs{{display:flex;gap:4px;margin-bottom:18px;background:#0d6e5f14;border-radius:10px;padding:4px}}
.tabs label{{flex:1;text-align:center;padding:9px;border-radius:8px;cursor:pointer;font-size:.92rem;user-select:none}}
input[name=tab]{{display:none}}
#t1:checked ~ .tabs label[for=t1], #t2:checked ~ .tabs label[for=t2]{{background:#0d6e5f;color:#fff}}
form{{display:none;flex-direction:column;gap:11px}}
#t1:checked ~ #f1, #t2:checked ~ #f2{{display:flex}}
input[type=text],input[type=password]{{padding:12px 13px;border-radius:10px;border:1px solid #ccd6d2;font-size:1rem;font-family:inherit}}
button{{padding:13px;border:0;border-radius:10px;background:#0d6e5f;color:#fff;font-size:1rem;cursor:pointer;margin-top:2px;font-family:inherit}}
button:active{{opacity:.85}}
.err{{background:#fde8e8;color:#a3231f;border-radius:9px;padding:9px 12px;font-size:.85rem;margin:0 0 6px}}
.hint{{font-size:.78rem;color:#7d968f;margin-top:-2px;line-height:1.5}}
</style></head><body>
<div class="card">
  <h1>📼 مقاطع</h1><p class="sub">مساحتك الخاصة لتفريغ وتقطيع الدروس</p>
  <input type="radio" name="tab" id="t1" {"checked" if tab == "1" else ""}>
  <input type="radio" name="tab" id="t2" {"checked" if tab == "2" else ""}>
  <div class="tabs"><label for="t1">دخول</label><label for="t2">حساب جديد</label></div>
  {err_html}
  <form id="f1" method="post" action="/gw/login">
    <input type="text" name="u" placeholder="اسم المستخدم" required autocomplete="username">
    <input type="password" name="p" placeholder="كلمة السر" required autocomplete="current-password">
    <button type="submit">دخول</button>
  </form>
  <form id="f2" method="post" action="/gw/register">
    <input type="text" name="u" placeholder="اسم المستخدم" required minlength="2" maxlength="30" autocomplete="username">
    <input type="password" name="p" placeholder="كلمة سر (٤ أحرف فأكثر)" required minlength="4" autocomplete="new-password">
    {invite_field}
    <button type="submit">إنشاء الحساب</button>
    <p class="hint">تُنشئ لك التطبيق مكتبة خاصة بك فورًا — لا يراها أو يستخدمها أحد غيرك.</p>
  </form>
</div>
</body></html>"""


# ---------- reverse proxy: forward an authenticated request byte-for-byte to that person's own process ----------
class LimitedReader:
    def __init__(self, rfile, n):
        self.rfile, self.left = rfile, n

    def read(self, size=-1):
        if self.left <= 0:
            return b""
        n = self.left if size is None or size < 0 else min(size, self.left)
        chunk = self.rfile.read(n)
        self.left -= len(chunk)
        return chunk


SKIP_REQ = {"host", "connection", "content-length"}
SKIP_RESP = {"connection", "transfer-encoding", "server", "date"}


def proxy(h, port):
    length = int(h.headers.get("Content-Length") or 0)
    headers = {k: v for k, v in h.headers.items() if k.lower() not in SKIP_REQ}
    headers["Host"] = f"127.0.0.1:{port}"
    if length:
        headers["Content-Length"] = str(length)
    body = LimitedReader(h.rfile, length) if length else None
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=180)
    try:
        conn.request(h.command, h.path, body=body, headers=headers)
        resp = conn.getresponse()
    except (ConnectionRefusedError, OSError, http.client.HTTPException):
        h.send_response(502)
        b = "الخادم الخاص بك يعيد التشغيل، حدّث الصفحة بعد لحظة.".encode("utf-8")
        h.send_header("Content-Type", "text/plain; charset=utf-8")
        h.send_header("Content-Length", str(len(b)))
        h.end_headers()
        h.wfile.write(b)
        conn.close()
        return
    h.send_response(resp.status)
    for k, v in resp.getheaders():
        if k.lower() not in SKIP_RESP:
            h.send_header(k, v)
    h.end_headers()
    if h.command != "HEAD":
        try:
            while True:
                chunk = resp.read(262144)
                if not chunk:
                    break
                h.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
    conn.close()


# ---------- HTTP plumbing ----------
def parse_cookies(header):
    out = {}
    for part in (header or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def set_cookie_header(token, clear=False):
    bits = [f"{COOKIE}={token if not clear else ''}", "Path=/", "HttpOnly", "SameSite=Lax"]
    bits.append("Max-Age=0" if clear else "Max-Age=31536000")
    if FORCE_HTTPS:
        bits.append("Secure")
    return "; ".join(bits)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "Maqati-Gateway"

    def log_message(self, *a):
        pass

    def do_GET(self): self.route()
    def do_POST(self): self.route()
    def do_PATCH(self): self.route()
    def do_DELETE(self): self.route()
    def do_HEAD(self): self.route()

    def is_https(self):
        return FORCE_HTTPS or self.headers.get("X-Forwarded-Proto") == "https"

    def send_html(self, code, body):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def redirect(self, loc, cookie_hdr=None):
        self.send_response(302)
        self.send_header("Location", loc)
        if cookie_hdr:
            self.send_header("Set-Cookie", cookie_hdr)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def form(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        return {k: v[-1] for k, v in parse_qs(raw.decode("utf-8", "replace")).items()}

    def route(self):
        try:
            path = urlparse(self.path).path
            if path == "/gw/login" and self.command == "POST":
                return self.do_login()
            if path == "/gw/register" and self.command == "POST":
                return self.do_register()
            if path == "/gw/logout":
                tok = parse_cookies(self.headers.get("Cookie")).get(COOKIE)
                if tok:
                    end_session(tok)
                return self.redirect("/", set_cookie_header("", clear=True))
            user = session_user(parse_cookies(self.headers.get("Cookie")).get(COOKIE))
            if not user:
                if path.startswith(("/api/", "/media/", "/export")):
                    # the app's own JS is asking — a plain 401 it can react to, not an HTML page it can't parse
                    b = b'{"detail":"auth"}'
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(b)))
                    self.end_headers()
                    return self.wfile.write(b)
                return self.send_html(200, login_page(tab="2" if path == "/gw/register" else "1"))
            uid, username = user
            try:
                port = ensure_backend(uid, username)
            except Exception:
                traceback.print_exc()
                return self.send_html(200, login_page(err="start"))
            proxy(self, port)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception:
            traceback.print_exc()
            try:
                self.send_html(500, "<p>خطأ غير متوقع.</p>")
            except Exception:
                pass

    def do_login(self):
        b = self.form()
        user = verify_user(b.get("u", ""), b.get("p", ""))
        if not user:
            return self.send_html(200, login_page(err="wrong", tab="1"))
        tok = new_session(user[0])
        self.redirect("/", set_cookie_header(tok))

    def do_register(self):
        b = self.form()
        if INVITE and b.get("inv", "") != INVITE:
            return self.send_html(200, login_page(err="invite", tab="2"))
        try:
            uid = create_user(b.get("u", ""), b.get("p", ""))
        except ValueError as e:
            return self.send_html(200, login_page(err=str(e), tab="2"))
        tok = new_session(uid)
        self.redirect("/", set_cookie_header(tok))


def main():
    port = int(os.environ.get("PORT") or os.environ.get("MAQATI_PORT") or 8080)
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=_reap, daemon=True).start()
    print(f"\n  Maqati gateway is running on :{port} — accounts kept in {DATA_ROOT}\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with _procs_lock:
            for info in _procs.values():
                try:
                    info["proc"].terminate()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
