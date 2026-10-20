"""Builds the iPhone version (a web app) into site/: the normal Maqati screens and engine, plus Pyodide (Python in
the browser) and ffmpeg.wasm. GitHub Pages publishes site/ (see .github/workflows/web.yml).

    python3 web/build.py [site_dir]

Downloaded packages are kept in web/.cache (or $WEB_CACHE)."""
import io
import json
import os
import re
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
APP = ROOT / "engine" / "app"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "site").resolve()
CACHE = Path(os.environ.get("WEB_CACHE") or HERE / ".cache")

PYODIDE = "0.27.7"
SQLITE = "sqlite3-1.0.0-cp312-cp312-pyodide_2024_0_wasm32.whl"
FF, FF_CORE = "0.12.15", "0.12.10"
GET = {
    "pyodide.tgz": f"https://registry.npmjs.org/pyodide/-/pyodide-{PYODIDE}.tgz",
    SQLITE: f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE}/full/{SQLITE}",
    "ffmpeg.tgz": f"https://registry.npmjs.org/@ffmpeg/ffmpeg/-/ffmpeg-{FF}.tgz",
    "ffmpeg-core.tgz": f"https://registry.npmjs.org/@ffmpeg/core/-/core-{FF_CORE}.tgz",
}
PY_FILES = ("pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json")
# absolute addresses of the normal app become relative, so the app works from any folder (github.io/maqati/)
ABS = re.compile(r"""(['"`(=])/(api|static|media|export)(?=[/?'"`])""")


def fetch(name):
    f = CACHE / name
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        print("download", GET[name])
        with urllib.request.urlopen(GET[name], timeout=300) as r:
            f.write_bytes(r.read())
    return f


def from_tgz(name, members):
    """{member path inside the package: where to put it}"""
    with tarfile.open(fetch(name)) as t:
        for m, dst in members.items():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(t.extractfile(m).read())


def rel(text):
    return ABS.sub(lambda m: m[1] + m[2], text)


def main():
    sys.path.insert(0, str(ROOT / "engine"))
    from app.version import VERSION
    stamp = VERSION + "-" + str(int(max(p.stat().st_mtime for p in list(APP.rglob("*")) + list(HERE.glob("*.*")))))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # the screens
    shutil.copytree(APP / "static", OUT / "static", ignore=shutil.ignore_patterns("sw.js", "offline.html"))
    for f in [OUT / "static" / "app.js", *(OUT / "static" / "guide").glob("*.html")]:
        f.write_text(rel(f.read_text(encoding="utf-8")), encoding="utf-8")
    man = json.loads((APP / "static" / "manifest.webmanifest").read_text(encoding="utf-8"))
    man.update(start_url="./", scope="./", name="مقاطع Maqati", short_name="مقاطع", background_color="#F6F3EC", theme_color="#0F5C4D")
    for i in man["icons"]:
        i["src"] = i["src"].lstrip("/")
    (OUT / "manifest.webmanifest").write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")

    html = (APP / "static" / "index.html").read_text(encoding="utf-8")
    html = html.replace('href="/static/manifest.webmanifest"', 'href="manifest.webmanifest"')
    html = rel(html).replace('<script src="static/app.js"></script>', "")
    html = re.sub(r'(static/(?:style|theme|fonts)\.css|static/(?:icons|reminders)\.js)"', rf'\1?v={stamp}"', html)
    boot = (HERE / "boot.html").read_text(encoding="utf-8").replace("__V__", stamp)
    html = html.replace("<body>", "<body>\n" + boot, 1)
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "404.html").write_text(html, encoding="utf-8")
    shutil.copy(HERE / "boot.js", OUT / "boot.js")
    (OUT / "sw.js").write_text((HERE / "sw.js").read_text(encoding="utf-8").replace("__V__", stamp), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")

    # the engine (Python files only; the screens are served above)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(APP.rglob("*.py")):
            text = f.read_text(encoding="utf-8")
            if f.name == "export.py":
                text = rel(text)
            z.writestr("app/" + f.relative_to(APP).as_posix(), text)
        for f in sorted((ROOT / "engine" / "vendor" / "qrcode").rglob("*.py")):
            z.writestr(f.relative_to(ROOT / "engine" / "vendor").as_posix(), f.read_bytes())
    (OUT / "engine.zip").write_bytes(buf.getvalue())

    # Python and ffmpeg for the browser
    from_tgz("pyodide.tgz", {f"package/{n}": OUT / "py" / n for n in PY_FILES})
    shutil.copy(fetch(SQLITE), OUT / "py" / SQLITE)
    with tarfile.open(fetch("ffmpeg.tgz")) as t:
        for m in t.getmembers():
            if m.isfile() and m.name.startswith("package/dist/esm/") and m.name.endswith(".js"):
                dst = OUT / "ff" / "ffmpeg" / Path(m.name).name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(t.extractfile(m).read())
    from_tgz("ffmpeg-core.tgz", {f"package/dist/esm/ffmpeg-core.{x}": OUT / "ff" / "core" / f"ffmpeg-core.{x}" for x in ("js", "wasm")})
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"built {OUT} · {stamp} · {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
