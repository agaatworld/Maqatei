"""Start a demo engine with a small library (for screenshots). Prints nothing; serves on the given port."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8770


def call(method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"null")


tmp = Path(tempfile.mkdtemp())
env = {**os.environ, "MAQATI_DATA": str(tmp / "data"), "MAQATI_LIBRARY": str(tmp / "lib"), "MAQATI_OPEN": "0",
       "MAQATI_PORT": str(PORT), "PYTHONPATH": str(ROOT / "engine" / "vendor")}
p = subprocess.Popen([sys.executable, "-m", "app.main"], cwd=ROOT / "engine", env=env,
                     stdout=subprocess.DEVNULL, stderr=open(tmp / "engine.log", "w"))
for _ in range(80):
    try:
        call("GET", "/api/health")
        break
    except Exception:
        time.sleep(0.25)
folders = {}
for name, color, icon in (("العقيدة", "#0F5C4D", "🕌"), ("الفقه", "#8A6A2B", "📖"), ("الحديث", "#1F4E79", "📚"), ("التفسير", "#4A5A66", "🌿")):
    fid = call("POST", "/api/folders", {"name": name})["id"]
    call("PATCH", f"/api/folders/{fid}", {"color": color, "icon": icon})
    folders[name] = fid
lessons = [("شرح كتاب التوحيد — الدرس الثالث", "العقيدة", 3760), ("فوائد من صحيح البخاري — كتاب العلم", "الحديث", 2895),
           ("أحكام الصيام — المجلس الأول", "الفقه", 4323)]
ids = []
for title, folder, d in lessons:
    f = tmp / f"{title}.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r=16000:cl=mono", "-t", str(d), "-b:a", "16k", str(f)], check=True)
    iid = call("POST", f"/api/upload?name={quote(f.name)}&folder_id={folders[folder]}", raw=f.read_bytes())["ids"][0]
    ids.append(iid)
call("PATCH", f"/api/items/{ids[0]}", {"pinned": True})
call("POST", f"/api/items/{ids[0]}/bookmarks", {"name": "معنى شهادة أن لا إله إلا الله", "start": 725.25, "end": 870})
call("POST", f"/api/items/{ids[0]}/bookmarks", {"name": "شروط لا إله إلا الله", "start": 1900, "end": 2292.5})
print(json.dumps({"ids": ids, "tmp": str(tmp)}), flush=True)
p.wait()
