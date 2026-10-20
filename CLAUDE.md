# Maqati — guide for Claude

The owner (GitHub `beaconcrest8`, earlier `turathpro`) is not technical. Reply in **simple Arabic**, short, numbered
steps, never ask him to run commands or build anything. He installs APKs from GitHub Releases.

The full product brief is in `docs/REBUILD-BRIEF.md`. Read sections 4 (features that must never be lost),
6 (transcription) and 9 (mistakes not to repeat) before changing anything.

## How it works
- `engine/app` is the Maqati engine (Python stdlib HTTP server + vanilla JS UI). Same code runs on PC.
- In the APK, `app/` (Kotlin) unpacks Python/ffmpeg/yt-dlp/QuickJS from youtubedl-android 0.18.1, copies
  `engine/` from assets, and runs `libpython.so -m app.main` with `MAQATI_*` env vars (see `Engine.kt`).
  `EngineService` (foreground service, type specialUse) keeps it alive; `MainActivity` shows it in a WebView.
- Version: `engine/app/version.py` is the single source (APK versionName/versionCode derive from it).
  Bump it + add a `## x.y.z` section to `CHANGELOG-ar.md` to publish a release (CI does it).
- Signing key in `signing/` must never change.

## Web version (iPhone and computer)
- https://beaconcrest8.github.io/maqati/open/ — the same engine in the browser: Pyodide runs `engine/app` (via
  `engine/app/webapi.py`), ffmpeg.wasm does media work, Groq is called from the page. Files live in IndexedDB.
- Sources: `web/` (boot.js, sw.js, boot.html, build.py). `python3 web/build.py` writes `open/` (committed; GitHub
  Pages publishes main). The web workflow rebuilds `open/` if it is stale. **`app/` is the Android project — never
  write build output there.**
- YouTube links on the web version go through the free mirrors (`mirrors.py`; the page fetches them all at once via
  `http_many`, ffmpeg.wasm gets the stream downloaded by the page). Other sites: not on the web. `tests/web/live.js` + `web-check.yml` (run it by hand:
  workflow_dispatch) use the live site and put screenshots in the `web-check` pre-release.

## Desktop app (Windows / Mac)
- `desktop/maqati_desktop.py` + `.github/workflows/desktop.yml`: PyInstaller one-file, pywebview window, imageio-ffmpeg,
  yt-dlp and Deno copied to `~/Maqati/.maqati/bin` on first run (so yt-dlp -U persists). Env `MAQATI_DESKTOP=1`,
  `MAQATI_YTDLP_EXE`, `MAQATI_DENO`. Uploaded to the version's GitHub release as Maqati-<v>-windows.exe / -mac-*.zip.

## Design rules from the owner
- **No eight-pointed stars or Islamic geometric motifs** anywhere (icons, patterns, backgrounds). He has refused them more than once.
- Few buttons; one button may open a page that leads to other pages. Compact, not "large mode".

## Before every push
- `PYTHONPATH=engine/vendor python3 tests/test_transcribe_pipeline.py`
- `node --check engine/app/static/app.js`
- CI builds, runs `tests/android/smoke.sh` on an emulator, uploads screenshots (`smoke-test` artifact). Look at them.
- No local Android build here: Google Maven is blocked in the cloud sandbox. CI is the build.
