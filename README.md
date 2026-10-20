# مقاطع · Maqati

تطبيق أندرويد لدروس العلم: أضف الدروس من يوتيوب أو من هاتفك، علّم المقاطع، قصّها صوتًا أو فيديو بأي جودة،
فرّغها نصًا بأوقات، ابحث في كل التفريغات، اجمع المقاطع في مشاريع، وصدّرها كتابًا (PDF / Word / TXT).

**التثبيت:** من صفحة [Releases](../../releases/latest) حمّل `maqati-…-arm64-v8a.apk` وافتحه.
لا يحتاج Termux ولا أي أوامر.

---

An Android app for Islamic lessons. No Termux: Python, yt-dlp, ffmpeg and QuickJS are packed inside the APK
(from [youtubedl-android](https://github.com/yausername/youtubedl-android)), and the Maqati engine runs in a
foreground service with the web interface in a WebView.

| Folder | What |
|---|---|
| `engine/app` | The Maqati engine (Python standard library) and its web interface (`static/`) |
| `engine/vendor` | `requests` and its pure-Python dependencies |
| `app/` | The Android app (Kotlin): starts the engine, keeps it alive, files, downloads, printing, updates |
| `tests/` | Engine tests and the emulator smoke test |
| `signing/` | The app's signing key. Never change it, or updates won't install over the old app |

Every push to `main` runs the tests, builds the APKs, tests them on an Android 14 emulator, and publishes
a release when `engine/app/version.py` has a new version.
