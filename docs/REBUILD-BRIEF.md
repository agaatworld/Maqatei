# مقاطع (Maqati): Full Rebuild Brief

> **For Claude Code.** This document is the complete brief for rebuilding Maqati from the ground up. The owner does not write code. He wants a finished, professional, easy app with **every feature it has today**, **no Termux**, **no bugs, lag or slowness**, and **transcription that is as close to 100% accurate as is technically possible**. Read everything before writing code. Section 9 lists mistakes that were already made; repeating any of them counts as a failure.

---

## 0. ملخص للمالك (بالعربي)

- **هل ممكن بدون Termux؟** نعم. الحل الأفضل: **تطبيق أندرويد حقيقي (APK)** فيه كل الأدوات من الداخل (أداة التنزيل yt-dlp وأداة القص ffmpeg)، عبر مكتبة جاهزة اسمها `youtubedl-android`، وهي نفس الطريقة اللي تستخدمها تطبيقات معروفة مثل Seal و YTDLnis. تثبّته مرة وحدة وتفتحه مثل أي تطبيق. ما في Termux ولا أوامر ولا "افتح Termux أولًا".
- **ليش مو موقع ويب؟** الموقع يقدر يقص ويفرّغ ملفات من جهازك، لكنه **ما يقدر ينزّل من يوتيوب**. المتصفح يمنع هذا، ويوتيوب يحظر خوادم السحابة ويطلب "تأكيد أنك لست روبوت". لهذا الويب خطة احتياطية فقط.
- **التفريغ (30% حاليًا):** وجدت أسبابًا تقنية واضحة في الكود الحالي تضعف الدقة (القسم 6). الخطة: اختبار عدة محركات تفريغ على **تسجيلاتك الحقيقية** واختيار الأدق، ثم مرحلة تصحيح ذكية تضبط الآيات والأحاديث والمصطلحات الشرعية، ثم تمييز الكلمات المشكوك فيها بلون حتى تصححها بلمسة.
  - **بصراحة:** لا يوجد محرك في العالم يعطي 100% دائمًا، خصوصًا مع الصوت الضعيف أو التلاوة أو اللهجة. لكن الهدف الواقعي **95% وأعلى** على الدروس الواضحة، وهذا فرق ضخم عن 30%.
- **التحديثات:** التطبيق الجديد يتحدّث من داخله بضغطة (يفحص GitHub ويثبّت النسخة الجديدة).

---

## 1. How to work with this owner (read first)

1. **The owner is non-technical.** He talks in casual Arabic, often with typos and long run-on messages. Every reply to him must be in **simple Arabic**, short, with numbered steps. Never ask him to run terminal commands unless there is truly no other way. If there is no other way, give one copy-paste block at a time and explain what success looks like.
2. **He tests on a real Android phone (Samsung-style UI, Android 14+), on a Windows PC, and on GitHub through a phone browser.** He has a GitHub account (`turathpro`) and a repo `turathpro/maqati-android` that already builds an APK with GitHub Actions.
3. **Every delivery must be complete and installable.** Do not hand him source code that he has to build. When he asked for an APK and got an Android Studio project, his reply was "فين apk؟؟" ("Where's the APK??").
4. **Test everything yourself before claiming it works.** Use real ffmpeg/yt-dlp runs, Playwright for UI at 390×844 in both dark and light mode, and real Arabic filenames. When something could not be tested (for example the real device), say so plainly.
5. **No regressions.** Before each release, run the full regression checklist (section 11). The cutting-speed regression in v3.4.0 and the dialog-closing bug in v3.3.0 both reached him because this step was skipped.
6. **Keep a CHANGELOG** in Arabic, written for him: what changed and what to do.

---

## 2. Product vision (what the owner wants)

Maqati is a personal, free **Arabic Islamic-lesson workstation**. You add lectures and lessons from YouTube or other sites, or from files on the phone. Then you can:

- play them
- mark parts with exact start and end times
- cut and download any part as MP3 or video, in any quality
- transcribe the whole lesson or any part into **precise Arabic text** with clickable timestamps
- search inside every transcript at once
- collect clips from many lessons into **projects**
- write benefits and notes
- export everything as a beautiful **book** (PDF, Word, TXT)

The owner's own words, which set the bar:

- «اريد هذا التطبيق بفعاليته وجميع ميزاته وتفاصيله … ويعمل … وما يعمل شيء ثاني! بدون تفريط ويكون فعال شغال ممتاز!» (all its power, all features and details; it just works with nothing else to do; no compromises; effective and excellent)
- «Now is 5% good. I want … 100% best!»
- «easy app no termux fully functional no bugs and errors or lags or slow, or either web if can't at all»
- «improve the current transcribe tool which is 30% accuracy … find alternative tool or do anything to raise it to 100% accurate!!!»

Target qualities: **simple, friendly, calm, professional, conventional structure, fast, reliable in the background, Arabic-first (RTL)**.

---

## 3. The current app (what exists today, v3.6.1)

### 3.1 Architecture

| Part | Today |
|---|---|
| Backend | Python standard-library `ThreadingHTTPServer` with a custom `@route(method, regex)` router (`app/main.py`, about 1,260 lines) |
| Storage | SQLite with WAL mode (`app/db.py`), one global connection, migrations through `ALTER TABLE` in a loop |
| Job queue | `app/jobs.py`: background threads, kinds `info / fetch / convert / clip / transcribe / project`, statuses `queued / running / paused / done / error / cancelled`, an ETA learned per task type, resume after restart |
| Media | `app/media.py`: wraps yt-dlp and ffmpeg as subprocesses; frame-accurate MP4 cuts without re-encoding by patching the MP4 edit list (`elst`); VBR/CBR-aware MP3 cuts; a stall watchdog |
| YouTube fallback | `app/mirrors.py`: Piped, Invidious and Cobalt public servers, used when YouTube shows the bot wall |
| Transcription | `app/transcribe.py`: Groq Whisper API (`whisper-large-v3`) or offline `faster-whisper` |
| Search | `app/search.py`: Arabic-normalised (ignores tashkeel and alef/yaa/taa-marbuta differences) |
| Export | `app/export.py`: book as printable HTML (to PDF), DOCX (hand-built XML) or TXT, with six fonts |
| Frontend | One vanilla JS single-page app (`app/static/app.js`, about 1,800 lines) with a hash router, `<dialog>` sheets, a global state object `S`, and a persistent floating player `PL` |
| Hosted mode | `app/gateway.py`: multi-user login with one isolated subprocess per user (built, but not used: hosting costs money and YouTube blocks servers) |
| Android | Termux runs the Python server, plus a WebView wrapper APK (`MaqatiAndroid`, Kotlin) that opens `http://127.0.0.1:8765` |
| Desktop | `.bat` / `.command` launchers that create a virtual environment and pip-install requirements |

### 3.2 Why the owner rates it "5%"

1. **Termux dependency.** He must install Termux, paste a long command, keep Termux alive and open it before the app. Android freezes or kills Termux in the background, so downloads die.
2. **Downloads hang for hours.** They show "downloading" but nothing happens. He has to reopen the app repeatedly until one attempt works. A watchdog was added in v3.6.1, but the root cause (Android killing the background process) remains with Termux.
3. **Transcription accuracy is about 30%** by his judgment (diagnosis in section 6).
4. **Installation pain:** unzip mistakes on Windows, pip cache warnings, Python on PATH, GitHub token pasting, and so on.
5. **The UI grew by accretion.** It works, but it is dense, inconsistent in places and not "professional/conventional".

---

## 4. Complete feature inventory: everything must survive the rebuild

> Treat this as the acceptance checklist. If a feature is dropped, the rebuild has failed.

### 4.1 Library and folders
- Folders with a name, colour (from a 4-colour calm palette) and icon. Customise, rename, delete.
- Library view toggle: grid of squares or a list.
- **Pin** the lesson currently being worked on, shown at the top of the library.
- "All" and "Unsorted" virtual folders.
- In each folder, a **"Works" (الأعمال) filter**: every transcript, audio cut and video cut made from that folder's lessons, gathered automatically. Each can be acted on as if it were in its normal place: play, rename, re-cut, transcribe, delete.
- "Transcribe all" for a folder.

### 4.2 Adding
- Paste one or many links (one per line): YouTube, SoundCloud and any site yt-dlp supports.
- Pick files from the phone (audio or video).
- Choose the target folder.
- Choose what happens to a new link: download video, download audio, or nothing (setting `auto_download`).
- Quality choice on add.

### 4.3 Lesson page (item)
- Rename the title by tapping it. Move to another folder with the folder chip.
- Collapsible sections, opened by tapping the heading itself (styled like a button, no separate toggle): **Parts & bookmarks, Transcript, Benefits & notes, Files, Tools**.
- Persistent player that keeps playing across pages, with a mini/dock player.
- Keyboard: Space = play/pause, ←/→ = skip by the user-configured amount, `,` and `.` = fine nudge.
- Configurable skip amount.

### 4.4 Marks and parts (cutting)
- 🔖 Bookmark the current moment. 🟢 Start then 🔴 End to make a part.
- **Type start and end times directly** (formats `1:05`, `1:02:30`, fractions such as `1:05.250`, Arabic comma accepted), not only buttons.
- After End, a popup to name the part, then Save / Save + MP3 / Save + transcribe / **Add to project**.
- **Fraction-of-a-second precision** for marking, scrubbing, and editing after the cut. A "re-set from player position" button, not typing only.
- Time ranges are shown as `1:05 – 2:30` (dash only, never "من … إلى").
- Per part: ▶ play, edit name or times, ⬇ MP3 / Video, 📝 transcribe, ➕ add to project, 💬 note.
- **Lock as done (✓):** a two-step confirm to lock, and again to unlock. Locked parts cannot be edited, renamed, re-cut or deleted.
- Multi-select parts for bulk download or transcription.
- Pad settings: seconds added before and after a search hit when making a clip (`pad_before = 3`, `pad_after = 5`).

### 4.5 Downloads and quality
- Download a whole video or audio, or **only a section** (fast: only those minutes are fetched).
- Convert MP4 to MP3.
- **A quality dropdown on every download button**, opening from the button itself: "⭐ Original (best)", then each real height the site offers (2160 → 144p), or a standard ladder when unknown. Audio: original / 192 / 128 / 96 / 64 kbps.
- Video cuts are **instant** (stream copy) with exact start and end through the MP4 edit list. Optional "re-encode for old players" setting (`reencode_video`, default off).
- Several downloads at once (setting `max_downloads = 3`).
- YouTube blocked: alternative player clients, then public mirror servers. Optional cookies upload.

### 4.6 Files section (per lesson)
- Every file of the lesson, grouped by type. Full-width titles, action icons bottom-right, groups collapse by tapping the heading.
- Clip popup: an independent player, edit start and end, re-cut, transcribe this clip, rename (renames sibling files of the same part), add to project.
- Save or share to the phone, open the folder.

### 4.7 Transcription
- Transcribe the whole lesson or any part, or many parts in bulk. Several at once (`max_transcribes = 2`).
- Transcript shown under the player. **The current sentence is highlighted as it plays; tap any sentence to seek there**; auto-follow can be toggled.
- ✏️ Edit the text inline.
- Transcript picker that shows **full, untruncated titles** in a smooth dropdown.
- Outputs `.txt` (with times) and `.srt`.
- Resume: finished pieces are kept if interrupted.
- Settings: engine, API key, model, language, custom vocabulary prompt.
- Test-transcription button in settings.

### 4.8 Benefits and notes, and excerpts
- Add a benefit or note, optionally linked to the current time. Edit, delete.
- Excerpts: a selected text range with title and note, which can be clipped to audio or video.

### 4.9 Search
- Search a topic across all transcripts. Separate synonyms with commas. Tashkeel and spelling variants are ignored.
- Scope: all folders or one folder.
- From each hit: ▶ listen, ➕ add to project, 🔖 mark.

### 4.10 Projects
- A project collects clips about one topic from many lessons. Name and description.
- **Optional sub-folders (sections)** inside a project. Rename them.
- Reorder with ▲▼ or drag. Move clips between sections.
- **Download all clips (ZIP):** cut, numbered and named, plus a Word book of their transcripts, with a progress bar.
- A single, unified "add to project" icon everywhere, and an "official"-looking projects icon (not a puzzle piece).

### 4.11 Export as a book
- Source: a lesson, a transcript, an excerpt set, a project, or a folder's excerpts.
- Options: title, subtitle, author, content (full / parts / both), paragraphs or lines, times on or off, cover page, contents page.
- **Custom paragraphs:** name each paragraph and set its own start and end. Optional and smooth to use.
- Separate font choices for headings and body in the export.
- Formats: PDF (print to PDF), Word (.docx, editable), TXT.

### 4.12 Tasks
- A Tasks page with everything running, queued, paused, failed or done.
- Pause / Resume / Cancel / Retry, bulk actions, "clear finished" (without deleting the files' links).
- **Live progress, time remaining (learned ETA), and time taken.**

### 4.13 Settings and look
- Language Arabic/English. Theme auto / light / dark / sepia. Accent colour. Font scale.
- Fonts (maximum 6 in total, a mix of traditional and modern light): IBM Plex Sans Arabic, Tajawal, Almarai, Amiri, Noto Naskh Arabic, Scheherazade New. **Separate choices for UI, headings and reading/transcripts.**
- **Dhikr reminder:** a small corner toast «لا حول ولا قوة إلا بالله» for 3 seconds every N minutes (default 15, 0 = off).
- Built-in illustrated user guide (Arabic and English) with screenshots.
- Updater (see section 10).

### 4.14 Things the owner explicitly asked for about the look
- «كل شي في الموقع جدا ضخم صغره قليلا ليس كثيرا» (everything is huge; shrink a little, not a lot)
- Replace heavy or bold fonts with light, comfortable ones.
- Reduce the palette to **4 calm colours**.
- Clearer download icon.
- Files-section buttons in the bottom corner, titles full width.

---

## 5. Architecture decision: getting rid of Termux

### 5.1 Options compared

| Option | YouTube download | Cut / convert | Transcribe | Background reliability | Cost | Verdict |
|---|---|---|---|---|---|---|
| **A. Native Android app with embedded yt-dlp + ffmpeg** (`youtubedl-android`) | ✅ from the phone's own home or mobile IP, which YouTube trusts most | ✅ ffmpeg bundled | ✅ cloud API | ✅ with a proper foreground service | Free | **Recommended** |
| B. Hosted website (server in the cloud) | ⚠️ cloud IPs get the "not a bot" wall often; needs paid residential proxies or cookies | ✅ | ✅ | ✅ | about $7–25 per month plus storage | Only if the owner later wants to share with many people |
| C. Pure in-browser web app (PWA, `ffmpeg.wasm`) | ❌ impossible (browser CORS rules plus YouTube protections) | ✅ local files only, slower | ✅ cloud API | ⚠️ browser tabs get suspended | Free (GitHub Pages) | Fallback for local files only |
| D. Keep Termux + WebView wrapper | ✅ | ✅ | ✅ | ❌ Android kills it | Free | What we have; rejected by the owner |

### 5.2 Recommended stack (Option A)

- **Language and UI:** Kotlin + **Jetpack Compose** + Material 3, RTL-first, Arabic fonts bundled.
  - Alternative if the existing web UI should be reused: a Kotlin shell hosting a local WebView UI. Compose is preferred for "professional, smooth, no lag".
- **Downloader + ffmpeg:** [`youtubedl-android`](https://github.com/yausername/youtubedl-android) (bundles Python 3.11, yt-dlp, ffmpeg 7 and aria2c; supports 16 KB page size as of 0.18.0; can update yt-dlp at runtime from stable or nightly channels). This is the library behind Seal and YTDLnis. Pin a version and verify it builds for `minSdk 24`, `targetSdk` current.
  - **Do not use FFmpegKit.** It was retired on 6 January 2025 and its binaries were scheduled for removal. FFmpegKitNext (July 2026) is source-only. ffmpeg from `youtubedl-android` covers the needs.
  - For simple trims, consider **AndroidX Media3 Transformer**, which can clip without full re-encoding. Benchmark it against ffmpeg stream copy and keep whichever is exact and fast.
- **YouTube JS challenges:** current yt-dlp needs a JavaScript runtime for YouTube challenges and PO tokens. `youtubedl-android` 0.18.1 added QuickJS. Confirm yt-dlp actually uses it (`-v` shows the runtime line). If it does not, every YouTube download degrades.
- **Database:** Room (SQLite). Port the current schema (section 3, file `app/db.py`) one-to-one so data can be imported from the old app.
- **Background work:** WorkManager plus a **foreground service** with a visible notification (progress, pause, cancel) for downloads, cuts and transcription. Use the correct foreground-service types (`dataSync`, and `mediaProcessing` for ffmpeg work on newer Android). **Check the current Android limits on dataSync foreground-service time** (Android 15 introduced daily time limits) and design around them: chunked work, resumable.
- **Storage:** app-private working directory, final files to the shared `Maqati` folder through MediaStore or the Storage Access Framework. **Arabic filenames must stay under 255 bytes** (current code caps at 110 bytes; keep that).
- **Secrets:** store API keys with the Android Keystore. Never log them.
- **Distribution:** GitHub Releases. The Play Store will not accept a YouTube downloader. **One fixed signing keystore** stored as GitHub Actions secrets; never lose or rotate it, or updates will fail to install over the old app.

### 5.3 If Option A is truly impossible: Option C fallback
A PWA on GitHub Pages that handles **local files only**: import, mark, cut with `ffmpeg.wasm`, transcribe through the cloud API, search, projects and export, with storage in IndexedDB/OPFS. State clearly in the UI that links (YouTube) are not supported on the web version. Check whether the chosen transcription API allows direct browser calls (CORS). If not, a tiny serverless proxy is needed, and the user's key must not be exposed to anyone else.

### 5.4 Desktop
Lower priority. If kept, ship the PC version as **one installer** (PyInstaller or similar) with Python, ffmpeg and yt-dlp inside. No `.bat` + pip + virtual environment (see the errors in section 9).

---

## 6. Transcription: from "30%" to as close to 100% as possible

> **Top priority after "no Termux".** The owner's content is Islamic lessons: Classical/Modern Standard Arabic mixed with dialect, Qur'an verses (often recited), hadith with chains of narration, du'a, scholars' names, and often echoing mosque audio or phone recordings.

### 6.1 Diagnosis of the current pipeline (concrete flaws found in the code)
1. **Hard-coded prompt on every chunk.** `_STYLE_AR = "الحمد لله، والصلاة والسلام على رسول الله. أما بعد:"` is prepended to every 8-minute piece (`transcribe.py`). Whisper treats the prompt as preceding text. This biases output and can cause hallucinated or duplicated openings. The previous chunk's real text is never passed as context.
2. **The cleaning step deletes real speech.** `clean()` drops any segment with `compression_ratio > 2.6` and drops a line repeated three times. In Islamic lessons, **repetition is genuine**: dhikr, "آمين", repeated verses, a teacher repeating a sentence for students. This silently loses content.
3. **Blind fixed-length chunks** (`CHUNK = 480` s, `OVERLAP = 5` s) cut mid-word. Overlap segments are kept or discarded by start time only, so words at borders are lost or doubled.
4. **Lossy double compression.** The source is re-encoded to 48 kbps MP3 at 16 kHz mono before upload. Use **FLAC/WAV at 16 kHz mono** (lossless; still small enough when chunked under the size limit).
5. **No voice-activity detection or noise handling.** Silence and music lead to Whisper hallucinations.
6. **Only segment-level times.** Word timestamps are available (`timestamp_granularities=word`) and would give precise highlighting and precise cuts from text.
7. **One engine, never benchmarked.** Groq `whisper-large-v3` was assumed best. Independent tests in 2026 rate Groq Whisper as **"poor/inconsistent"** for Arabic compared with newer engines (see sources).
8. **No post-correction.** Qur'an verses, hadith and names come out misspelled with no fixing step.

### 6.2 The plan
**Step 1: build a benchmark before choosing anything.**
- Ask the owner for 5–10 representative recordings (a clear lecture, a phone recording, a mosque echo, Qur'an recitation, dialect Q&A), 2–5 minutes each.
- Create reference transcripts. The owner corrects an initial draft once; this is the "truth".
- Measure **WER and CER** after Arabic normalisation (same normaliser as `search.py`). Report per recording and per engine in a table. Pick by numbers, not by marketing.

**Step 2: candidate engines to test (verify current model names and prices at build time):**

| Engine | Why test it |
|---|---|
| Groq `whisper-large-v3` (current baseline) | Cheap ($0.111/hour), fast, free tier, 25 MB per file on free tier |
| ElevenLabs Scribe | Strong multilingual; Arabic page claims high accuracy |
| Google Gemini (latest Pro/Flash with audio input) | Long context; can transcribe **and** apply Islamic-text instructions in one pass |
| OpenAI `gpt-4o-transcribe` (or its successor) | Strong accuracy in published comparisons |
| Soniox | Lowest measured WER (16.2%) in a 2026 Arabic test |
| Deepgram Nova-3, Speechmatics, Google Chirp 3, Azure | Arabic and dialect support |
| Audar-ASR-V1 (open weights; #1 on the Open Universal Arabic ASR Leaderboard, 24.78% average WER) | Also has a hosted API; a possible free or offline route on PC |
| Tarteel or a Qur'an-specific model | For recited verses only |

**Step 3: pipeline improvements, whatever engine wins.**
- Split on **silence** (VAD), not fixed time. Pieces of about 30–120 s, never cutting words. Keep a small overlap and merge by **word timestamps** with text alignment.
- Pass the **previous piece's last sentences** as context; never a fixed phrase. Allow a user **glossary** (scholar names, book titles, places) as the vocabulary prompt.
- Lossless 16 kHz mono input. Optional light noise reduction and loudness normalisation (A/B test that it helps, not hurts).
- Remove only true hallucinations (known junk phrases on silent or music-only regions). **Never delete repeated speech.**
- Request **word-level timestamps** and store them.

**Step 4: smart correction pass (optional toggle, on by default).**
- Send each piece's text to an LLM (for example Claude or Gemini) with strict instructions: fix spelling and punctuation; **do not add, remove or reorder spoken content**; keep dialect as spoken; mark unsure words.
- **Qur'an snapping:** detect verse fragments, match them against a bundled verified Qur'an text (Uthmani, from a trusted dataset such as Tanzil), and replace with the exact verse plus a reference (surah:ayah). Same idea for common du'a and hadith formulas (صلى الله عليه وسلم, رضي الله عنه, and so on).
- Keep the raw engine output stored too, so a correction can always be undone.

**Step 5: make the remaining errors trivial to fix.**
- Highlight low-confidence words (word confidence from the engine) in a soft colour.
- Tap a word → play exactly that moment → type the fix. The edit updates `.txt`, `.srt`, search and export.

**Step 6: be honest in the UI.**
Show which engine was used and an estimated quality. **No engine guarantees 100%.** The goal is ≥95% word accuracy on clear lessons, measured on the owner's own benchmark. Report the real numbers to the owner.

### 6.3 Cost and keys
Keep a free path (Groq free tier) and let the owner add a key for a more accurate paid engine. Show the estimated cost per hour of audio next to each engine in settings. Handle rate limits by waiting and continuing automatically (the current behaviour on 429 is good; keep it).

---

## 7. Downloads: must never hang

### 7.1 Root causes seen
- A connection silently dies (Wi-Fi ↔ mobile switch, phone sleeps) and yt-dlp waits forever with no error. **Fixed in v3.6.1** with a 120-second no-output watchdog that kills and resumes with `-c`. Keep this behaviour.
- Android freezes or kills the background process (Termux, battery optimisation, Samsung "sleeping apps", the phantom-process killer on Android 12+). **The native app plus a foreground service solves this.** Also prompt the user once to exempt the app from battery optimisation, with a clear Arabic explanation.

### 7.2 Requirements
- Resume from partial files after any interruption, app restart or reboot (WorkManager re-enqueue).
- A visible notification with real progress, speed, ETA, pause and cancel.
- Retry with back-off. Classify errors: network, blocked by YouTube, not available, disk full. Show a human Arabic message for each with the next action.
- **YouTube block strategy:** phone IP first, then alternative player clients, then a working JS runtime / PO token provider, then optional cookies (warn: use a spare account), then public mirrors. Auto-update yt-dlp at most daily in the background (YouTube changes often).
- Section downloads (only the chosen minutes) must stay fast.
- Never show "downloading" without progress for more than about 2 minutes. Either progress moves or the user sees "connection lost, continuing…".

---

## 8. UI / UX requirements

- **Arabic-first RTL**, English available. Everything reachable with one hand. Bottom tabs: **Library, Search, Projects, Tasks**, with Settings in the header.
- **Design system:** 4 calm colours plus neutrals; light, dark and sepia themes; the 6 fonts listed (light weights by default); 8-point spacing; consistent icons (one icon set; one "add to project" icon; a formal projects icon).
- **Sizes:** slightly smaller than v3 ("shrink a little, not a lot"); minimum touch target 44–48 dp.
- **Feedback:** every tap responds within 100 ms; skeleton loaders; toasts for background actions; no blocking spinners for background work.
- **Smoothness:** no jank in lists (lazy lists, paging); the player never stutters during downloads or transcription.
- **Dialogs never close unexpectedly** while background refresh happens (a real bug in v3.3.0; section 9).
- **Accessibility:** contrast AA, scalable fonts, content descriptions.
- **Onboarding:** a 3-screen first-run guide (add a link, mark a part, transcribe), plus key setup with a "test" button.
- **Empty states and errors** written in friendly Arabic, each with a suggested action.

---

## 9. Errors and lessons learned (do not repeat)

| # | What happened | Lesson / rule |
|---|---|---|
| 1 | v3.3.0: a line added only for automated testing (`route()` closed any open dialog) closed the user's "Add"/"New folder" dialog every 1.5 s during downloads | Never ship test-only hacks. Grep for them before every release. |
| 2 | v3.4.0: made every video cut re-encode for precision; cutting became very slow («القص اصبح بطيء») | Measure speed before and after every media change. Precision came from the MP4 edit-list method with **no** re-encode. |
| 3 | v3.4.0: a duplicate keyboard handler made Space unreliable and arrows skip double | One global input handler. Test keyboard shortcuts in the regression suite. |
| 4 | v3.5.0: the user could not see the new quality dropdown («لا اجد السهم ولا الخيارات») because of a cached old `app.js` | Version every asset (cache-busting); the service worker must not serve stale code. Native app: not applicable, but the updater must replace everything. |
| 5 | Audit found 10 bugs: "clear tasks" deleted file links, stale item state after navigation, cross-project job leak (LIKE match), empty "all excerpts" export, crash on save after navigating away, 500 instead of 4xx, redundant re-renders, ZIP progress not tracked, rename not applied to sibling files, stale search scope | Write tests for each. Guard every async UI update against the user having navigated away. |
| 6 | Cuts were off by fractions of a second | Fraction-precise times everywhere (store as float seconds; display `m:ss.mmm` when editing). VBR MP3 needs decode-accurate seeking. |
| 7 | Downloads hung for hours (silent dead connections plus Android killing Termux) | Watchdog + resume + foreground service (section 7). |
| 8 | Windows: `requirements.txt` not found because the user ran the `.bat` from inside the zip | Ship one installer; never rely on the user extracting correctly. |
| 9 | Windows: many `pip` "Cache entry deserialization failed" warnings scared the user | Hide harmless noise; show one clear progress line. |
| 10 | Android build: the sandbox could not reach Google or Gradle servers, so the APK was never compiled before delivery | Build in **GitHub Actions** (works) and test the APK in an emulator in CI before release. |
| 11 | GitHub web upload of a project with many folders failed from the phone; a zip upload is not extracted | Give the owner a ready repo; avoid manual uploads. |
| 12 | Pushing from Termux: git missing, "dubious ownership", no identity, the user typed the wrong username (`turath` vs `turathpro`), the token could not be pasted into the hidden password prompt, the remote had a README so the push was rejected | Script the whole thing or avoid it; never require the owner to use git. |
| 13 | The owner's GitHub token appeared in screenshots | Remind him to revoke and recreate it. Never ask for tokens in chat. Use Actions secrets. |
| 14 | The `.github/workflows` file was missing from his zip/repo, so Actions showed "Get started" | Verify the repo contents after setup (list the workflow file). |
| 15 | Transcription prompt and cleaning heuristics reduced accuracy (section 6.1) | Benchmark every transcription change on the owner's real audio. |
| 16 | Free hosting (Render free tier, Fly.io) wipes files or no longer exists | Do not promise free hosting for a backend app. |

---

## 10. Updates and distribution
- GitHub Actions builds a **signed release APK** on every tag. Run unit tests, a lint check and an emulator smoke test, then publish to **GitHub Releases** with Arabic release notes.
- **In-app updater:** on launch (and from Settings → Update), check the latest GitHub Release. If newer, show the notes and offer "Update"; download and launch the system installer. Keep the user's library, database and settings.
- **Same signing key forever** (Actions secrets plus an offline backup), or Android refuses the update.
- Import tool: read the old app's `maqati.db` and library folder so the owner keeps all existing lessons, marks, transcripts and projects.

---

## 11. Quality bar and definition of done
- **Regression checklist (run before every release):**
  - add a YouTube link and a local file
  - download a full video and a section in two qualities
  - cut MP3 and video parts with fractional times; verify durations with ffprobe to ±0.05 s
  - lock and unlock a part
  - transcribe a part and a full lesson
  - search Arabic with variant spelling
  - build a project with sections and export the ZIP
  - export PDF, DOCX and TXT with custom paragraphs
  - pause, kill the app, reboot, and check that work resumes
  - switch Wi-Fi to mobile mid-download and check it continues
  - check dark, light and sepia; Arabic and English
- **Performance:** cold start under 2 s on a mid-range phone; scrolling at 60 fps; cuts of local files near-instant (stream copy).
- **Transcription:** report WER/CER per engine on the owner's benchmark. Ship the best. Target ≥95% word accuracy on clear lessons.
- **Zero crashes** in the smoke tests; all errors shown in friendly Arabic.

---

## 12. Suggested phases
1. **Phase 0 (1 session):** transcription benchmark harness plus the owner's sample audio. Run all candidate engines and report the table.
2. **Phase 1:** native app skeleton: library, add link or file, download with notification and resume, player. Ship an APK through Actions plus the updater.
3. **Phase 2:** marks and parts, precise cutting, quality dropdown, Files section, lock.
4. **Phase 3:** the new transcription pipeline (section 6) with the winning engine, the correction pass and the confidence-highlight editor.
5. **Phase 4:** search, notes and excerpts, projects with sections and ZIP, export book with custom paragraphs and fonts.
6. **Phase 5:** polish: design system, onboarding, dhikr reminder, guide, import from the old app, full regression, release 4.0.

Deliver an installable APK at the end of **every** phase so the owner can try it.

---

## 13. Appendix: the owner's messages (chronological, verbatim where available)

**Features and design (v3.2 → v3.5):**
- «اريد عند الضغط على ما انجزه ان يظهر لي نافذة منبثقة فيها المقطع الجاهز مستقل! وهناك خياران لتعديل بداية ونهاية المقطع مع زر لتفريغه الخاص… اقدر اعدل اسماء كل مقطع! … خيار لاضافة كل مقطع في المشروع … داخل كل مشروع … خيار اختياري لعمل مجلدات فرعية … لما اختار مقطع بداية ونهاية يظهر لي نافذة منبثقة لاكتب اسمها … المجلدات في المكتبة اريد زر في الاعلى لعرض المجلدات كقائمة او مربعات! … كل شي في الموقع جدا ضخم صغره قليلا ليس كثيرا!»
- «في كل مجلد اريد في التصفية زر يظهر لي كل الاعمال التي تمت في هذا المجلد تفريغات او صوتيات او مرئيات مقطعة … فيها اقدر اعمل اي حاجة كانهم في مكانهم الطبيعي.»
- The big batch: full transcript titles in a smooth dropdown; Files buttons at the bottom with full-width titles; a clearer download icon; a ✓ done lock with a second confirm press; light comfortable fonts; separate fonts for headings, body and export; named paragraphs with custom start and end for export; maximum 6 fonts mixing traditional (Amiri, Lotus-like) and modern light; 4 calm colours; a unified add-to-project icon; a formal projects icon instead of a puzzle piece; collapse sections by tapping the heading; times with a dash instead of "from … to"; pin the current lesson; the dhikr reminder every 10–15 minutes for 3 seconds (configurable).
- «هل يظهر كم وقت متبقي وكم قد استغرق لينتهي؟» (shows time left and time taken: keep this)
- «لما احمل رابط فيديو يحصل مشاكل ما اقدر اضيف اي شي ولا انشيء مجلد بيحصل اضطرابات!» (bug 1)
- «التطبيق يقدم او يؤخر اجزاء من الثانية عند القص المرئي او الصوتي اريد … دقيقة على حسب اجزاء من الثانية وكذلك تحريك المشغل! وحتى التعديل بعد القص … وبعد القص اريده يكون هناك زر لاعادة تحديد البداية والنهاية ليس كتابة فقط … وعند القص الاولي لا اريد يكون عبارة عن ازرار فقط بل … خيار لكتابة بداية ونهاية المقطع!»
- «القص اصبح بطيء خاصة الان جربت القص المرئي من اليوتيوب ابطأ من قبل!» (bug 2)
- «اريد خيار تحميل اي شيء بجودة محددة تبدأ من جودة المقطع الاصلي ثم تنزل لاقل جودة! اختيار من قائمة منسدلة تنزل من التحميل! وضبط لو في اشي خربان او اي باجز او ايرورز»
- «لا اجد السهم ولا الخيارات؟!!» (bug 4)

**Sharing, GitHub and hosting:**
- Asked how to put it on GitHub, whether it helps, whether it is faster or slower for people he shares with, whether internet is needed, and «لما اعمله كرابط واشاركه لصديقي».
- «اريد هذا التطبيق بفعاليته وجميع ميزاته وتفاصيله كملف ارفقه لجتهب ويعمل عن طريق اي شخص اخر يضغط الرابط وما يعمل شيء ثاني! بدون تفريط ويكون فعال شغال ممتاز!» He chose hosting with a separate private space per person, then copy-paste git commands.

**Installation problems (Windows):**
- `ERROR: Could not open requirements file … requirements.txt` («THIS WHAT HAPPENED FOR FIRST METHOD»)
- Repeated `WARNING: Cache entry deserialization failed, entry ignored`

**Android APK:**
- «Now make an apk app for this maqati latest version with ability to update … Same everything!!»
- «اريد ملف Apk للموقع بنفس الميزات كلها وانا احمله يدويا»
- «فين apk؟؟» · «Too many files to add. Is it enough to add zip» · «I can't paste the token» · «لما افتحه يفتح لي /new» · «تمام بيشتغل» · «تم شكرا»

**Downloads:**
- «When I download anything it shows it downloading but it's not and takes hours and need to open back the app every period to redownload until 1 time it works!!!»

**This rebuild request:**
- «Is it possible to make the app on web so no need termux? What to do to avoid termux. Make md and all info needed and all precautions and errors done to avoid and my comments detailed and your process … for me to resend to claude code for it to rebuild in the best way and make my goals in professional way, conventional structure, design simple and all features and friendly interface. Now is 5% good. I want … 100% best!»
- «I want him to make either easy app no termux fully functional no bugs and errors or lags or slow, or either web if can't at all. And also the Claude Code make all its effort to improve the current transcribe tool which is 30% accuracy to find alternative tool or do anything to raise it to 100% accurate!!!»

---

## 14. Reference: the current code
The current code (v3.6.1, Python + JS) is in the owner's `maqati.zip`, and the Android wrapper is in `turathpro/maqati-android`. Use them as the **functional specification** (behaviour, the database schema in `app/db.py`, the export layout in `app/export.py`, the Arabic search normalisation in `app/search.py`, and the MP4 edit-list trick `trim_edit_end` in `app/media.py`). Do not port their structure blindly; rebuild cleanly.

## 15. Sources (checked October 2026; re-verify at build time)
- youtubedl-android (yt-dlp + ffmpeg + Python for Android): https://github.com/yausername/youtubedl-android and releases https://github.com/yausername/youtubedl-android/releases
- YTDLnis (an app built on it): https://ytdlnis.org/download
- FFmpegKit retirement and FFmpegKitNext: https://tanersener.medium.com/saying-goodbye-to-ffmpegkit-33ae939767e1
- YouTube "not a bot" wall, datacenter IPs, PO tokens, JS runtime: https://tunelio.dev/blog/yt-dlp-sign-in-to-confirm-not-a-bot/
- Groq speech-to-text limits and prices: https://console.groq.com/docs/speech-to-text
- Arabic STT comparison 2026 (Gulf Arabic, voice-agent test): https://voicearabic.com/en/guides/best-arabic-stt-api-2026
- Speech-to-text leaderboard: https://artificialanalysis.ai/speech-to-text/non-streaming
- Open Universal Arabic ASR Leaderboard: https://github.com/Natural-Language-Processing-Elm/open_universal_arabic_asr_leaderboard
- Audar-ASR-V1: https://github.com/AudarAI/Audar-ASR-V1
- ElevenLabs Arabic STT: https://elevenlabs.io/speech-to-text/arabic
