"""Open Maqati from an iPhone (or any phone, tablet or computer) on the same Wi-Fi.

A second door on the home network (port 8766), separate from the app's own 127.0.0.1:8765. It asks for a
6-digit code once per device (kept in a cookie), so nobody else on the Wi-Fi can open your library."""
import hashlib
import os
import secrets
import socket
import threading
import time
from http.server import ThreadingHTTPServer

from . import db

PORT = int(os.environ.get("MAQATI_LAN_PORT", "8766"))
_srv = None
_lock = threading.Lock()
_fails = {}                          # ip -> [count, first failure time]
# routes a device on the Wi-Fi may never use: they change this door itself or the app's own files
BLOCKED = ("/api/lan", "/api/open-folder", "/api/update", "/api/update-downloader")
OPEN = ("/lan-login", "/static/icon-192.png", "/static/icon-512.png", "/static/fonts.css", "/static/fonts/")


def local_ip():
    """This device's address on the Wi-Fi (no data is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def code():
    s = db.get_settings()
    c = str(s.get("lan_code") or "")
    if len(c) != 6 or not c.isdigit():
        c = f"{secrets.randbelow(10 ** 6):06d}"
        db.set_settings({"lan_code": c})
    return c


def token(c=None):
    return hashlib.sha256(("maqati-lan:" + (c or code())).encode()).hexdigest()[:32]


def url():
    ip = local_ip()
    return f"http://{ip}:{PORT}/" if ip else None


def qr_svg(text):
    """A QR code as SVG (scanned by the iPhone camera to open the address)."""
    import qrcode
    q = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(text)
    q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    path = "".join(f"M{x},{y}h1v1h-1z" for y, row in enumerate(m) for x, v in enumerate(row) if v)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges" role="img" '
            f'aria-label="QR"><rect width="{n}" height="{n}" fill="#fff"/><path d="{path}" fill="#000"/></svg>')


def status():
    on = _srv is not None
    out = {"on": on, "port": PORT}
    if on:
        u = url()
        out.update(code=code(), url=u, qr=qr_svg(u) if u else None)
    return out


def start(handler_cls):
    global _srv
    with _lock:
        if _srv:
            return True
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", PORT), handler_cls)
        except OSError:
            return False
        srv.daemon_threads = True
        srv.maqati_lan = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _srv = srv
        code()
        return True


def stop():
    global _srv
    with _lock:
        if _srv:
            _srv.shutdown()
            _srv.server_close()
            _srv = None


def allowed(h, path):
    """For requests that came over the Wi-Fi: may this one go through?"""
    if path.startswith(OPEN):
        return True
    if path.startswith(BLOCKED):
        return False
    ck = h.headers.get("Cookie") or ""
    want = "mq_lan=" + token()
    return any(p.strip() == want for p in ck.split(";"))


def try_login(h, entered):
    ip = h.client_address[0]
    n, t0 = _fails.get(ip, [0, time.time()])
    if time.time() - t0 > 600:
        n, t0 = 0, time.time()
    if n >= 8:                                    # too many wrong codes: wait 10 minutes
        return False
    if secrets.compare_digest((entered or "").strip(), code()):
        _fails.pop(ip, None)
        return True
    _fails[ip] = [n + 1, t0]
    time.sleep(1)
    return False


def login_page(wrong=False):
    msg = '<p class="e">الرمز غير صحيح. حاول مجددًا. / Wrong code.</p>' if wrong else ""
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>مقاطع</title>
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="مقاطع">
<link rel="apple-touch-icon" href="/static/icon-192.png"><link rel="stylesheet" href="/static/fonts.css">
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#F6F3EC;color:#1B2420;font:17px/1.7 Plex,system-ui,sans-serif;padding:24px;box-sizing:border-box}}
.c{{width:100%;max-width:360px;text-align:center}}.l{{width:72px;height:72px;border-radius:22px;background:#10352E;color:#D6B46A;display:grid;place-items:center;margin:0 auto 16px;font:700 34px Amiri,serif}}
h1{{margin:0 0 6px;font-size:24px}}p{{margin:0 0 18px;color:#66706B}}input{{width:100%;box-sizing:border-box;height:64px;border-radius:18px;border:1px solid #E8E2D5;background:#fff;text-align:center;font-size:30px;letter-spacing:.3em;direction:ltr}}
input:focus{{outline:0;border-color:#0F5C4D;box-shadow:0 0 0 4px rgba(15,92,77,.15)}}button{{width:100%;height:56px;margin-top:12px;border:0;border-radius:18px;background:#0F5C4D;color:#fff;font:inherit;font-weight:600}}
.e{{color:#9E3B2C}}</style></head><body><form class="c" method="post" action="/lan-login"><div class="l">م</div>
<h1>مقاطع</h1><p>اكتب الرمز الظاهر في «مقاطع» على هاتفك (الإعدادات ← فتح من جهاز آخر).</p>{msg}
<input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]*" autofocus required>
<button>دخول</button></form></body></html>"""
