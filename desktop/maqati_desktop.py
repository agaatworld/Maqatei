"""Maqati for Windows and Mac: one program that starts the engine and shows it in its own window.
Built by PyInstaller in .github/workflows/desktop.yml, with ffmpeg (imageio-ffmpeg), yt-dlp and Deno inside.
Your files: the Maqati folder in your home folder."""
import os
import shutil
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

if sys.stdout is None:                      # a windowed program has no console
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
HOME = Path.home() / "Maqati"
DATA = HOME / ".maqati"
DATA.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MAQATI_LIBRARY", str(HOME))
os.environ.setdefault("MAQATI_DATA", str(DATA))
os.environ.setdefault("MAQATI_PORT", "8765")
os.environ["MAQATI_OPEN"] = "0"
os.environ["MAQATI_DESKTOP"] = "1"
EXE = ".exe" if sys.platform == "win32" else ""


def tool(name, var):
    """A bundled program, copied once beside the data (so yt-dlp can update itself and the copy stays)."""
    src = HERE / "bin" / (name + EXE)
    if not src.exists():
        return
    dst = DATA / "bin" / (name + EXE)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or (name != "yt-dlp" and dst.stat().st_size != src.stat().st_size):
        shutil.copy2(src, dst)
    if EXE == "":
        os.chmod(dst, 0o755)
    os.environ.setdefault(var, str(dst))


tool("yt-dlp", "MAQATI_YTDLP_EXE")
tool("deno", "MAQATI_DENO")
try:
    import imageio_ffmpeg
    os.environ.setdefault("MAQATI_FFMPEG", imageio_ffmpeg.get_ffmpeg_exe())
except Exception:
    pass

sys.path.insert(0, str(HERE))
from app import main as engine  # noqa: E402

PORT = int(os.environ["MAQATI_PORT"])
URL = f"http://127.0.0.1:{PORT}/"
threading.Thread(target=engine.main, daemon=True).start()
for _ in range(150):
    try:
        urllib.request.urlopen(URL + "api/health", timeout=2).read()
        break
    except Exception:
        time.sleep(0.2)



def browser():
    """Edge or Chrome, if installed: the app opens in its own window (fast, nothing to install)."""
    import shutil
    cands = []
    if sys.platform == "win32":
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                cands += [Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe", Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"]
    elif sys.platform == "darwin":
        cands += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"), Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")]
    else:
        cands += [Path(p) for p in (shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("microsoft-edge")) if p]
    return next((str(c) for c in cands if c.exists()), None)


def idle_exit():
    """No page open for two minutes and nothing running: stop (the window was closed)."""
    while True:
        time.sleep(15)
        busy = engine.db.one("SELECT 1 FROM jobs WHERE status IN ('running','queued')")
        if time.time() - engine.LAST > 120 and not busy:
            os._exit(0)


exe = browser()
if exe:
    import subprocess
    prof = DATA / "browser"
    prof.mkdir(exist_ok=True)
    p = subprocess.Popen([exe, f"--app={URL}", "--start-maximized", f"--user-data-dir={prof}", "--no-first-run", "--no-default-browser-check"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    threading.Thread(target=idle_exit, daemon=True).start()
    p.wait()
    time.sleep(2)
    busy = engine.db.one("SELECT 1 FROM jobs WHERE status IN ('running','queued')")
    while busy:                                 # the window closed while something runs: finish it first
        time.sleep(10)
        busy = engine.db.one("SELECT 1 FROM jobs WHERE status IN ('running','queued')")
else:
    try:
        import webview
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.create_window("مقاطع · Maqati", URL, width=1280, height=840, min_size=(860, 600), maximized=True)
        webview.start()
    except Exception:                           # no window library: the normal browser instead
        webbrowser.open(URL)
        idle_exit()
engine.jobs.stop_all()
time.sleep(0.5)
os._exit(0)
