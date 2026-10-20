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

try:
    import webview
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.create_window("مقاطع · Maqati", URL, width=1280, height=840, min_size=(860, 600))
    webview.start()
except Exception:                           # no window library: the normal browser instead
    webbrowser.open(URL)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
engine.jobs.stop_all()
time.sleep(0.5)
os._exit(0)
