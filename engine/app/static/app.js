/* Maqati — interface. Plain JavaScript, no build step. */
'use strict';
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const encURI = p => p.split('/').map(encodeURIComponent).join('/');
const store = { get(k, d) { try { const v = localStorage.getItem('mq.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('mq.' + k, JSON.stringify(v)); } catch (e) {} } };

/* ================= words (English / Arabic) ================= */
const TX = {
  app: ['Maqati', 'مقاطع'], tagline: ['In the name of Allah', 'بسم الله'],
  library: ['Library', 'المكتبة'], search: ['Search', 'البحث'], projects: ['Projects', 'المشاريع'], tasks: ['Tasks', 'المهام'],
  settings: ['Settings', 'الإعدادات'], help: ['How to use', 'دليل الاستخدام'],
  all_items: ['All', 'الكل'], unsorted: ['Unsorted', 'غير مصنّف'], new_folder: ['New folder', 'مجلد جديد'],
  home: ['Home', 'البداية'], menu: ['Menu', 'القائمة'], now_running: ['Running now', 'جارٍ الآن'], nothing_running: ['Nothing is running. Cuts and transcriptions you start will show here.', 'لا شيء يعمل الآن. ما تبدؤه من قصّ أو تفريغ يظهر هنا.'],
  recent_works: ['Your latest works', 'أحدث أعمالك'], your_folders: ['Your folders', 'مجلداتك'], see_all: ['All', 'الكل'], home_search_ph: ['Search every transcript…', 'ابحث في كل التفريغات…'],
  first_lesson: ['Add your first lesson', 'أضف أول درس'], first_lesson_p: ['A recording from your device, or a link.', 'تسجيلًا من جهازك أو رابطًا.'],
  recent: ['Recently added', 'أُضيف مؤخرًا'], items_n: ['{0} items', '{0} عناصر'], add: ['Add', 'إضافة'],
  empty_lib: ['Your library is empty', 'مكتبتك فارغة'], empty_lib_p: ['Add a YouTube link, a SoundCloud link, or a file from your device.', 'أضف رابط يوتيوب أو ساوند كلاود أو ملفًّا من جهازك.'],
  empty_folder: ['Nothing here yet — tap “Add”.', 'لا شيء هنا بعد — اضغط «إضافة».'],
  marks_n: ['{0} parts', '{0} مقاطع'], has_tr: ['transcribed', 'مُفرَّغ'], reading: ['reading link…', 'قراءة الرابط…'],
  customize: ['Customize', 'تخصيص'], transcribe_all: ['Transcribe all', 'فرّغ الكل'], delete: ['Delete', 'حذف'],
  filter: ['Filter…', 'تصفية…'], newest: ['Newest', 'الأحدث'], by_name: ['Name', 'الاسم'],
  folder_name: ['Folder name', 'اسم المجلد'], color: ['Color', 'اللون'], icon: ['Icon', 'الأيقونة'], save: ['Save', 'حفظ'], cancel: ['Cancel', 'إلغاء'],
  del_folder_q: ['Delete this folder? Its items are kept (moved to Unsorted).', 'حذف هذا المجلد؟ العناصر تبقى (تنتقل إلى غير مصنّف).'],
  queued_n: ['{0} added to Tasks', 'أُضيفت {0} إلى المهام'], nothing_to_do: ['Everything here is already transcribed', 'كل ما هنا مُفرَّغ مسبقًا'],
  links: ['Links', 'روابط'], files: ['Files', 'ملفات'], links_ph: ['Paste one or many links — one per line', 'الصق رابطًا أو أكثر — كل رابط في سطر'],
  links_hint: ['YouTube, SoundCloud and most audio/video sites.', 'يوتيوب وساوند كلاود ومعظم مواقع الصوت والمرئي.'],
  links_hint_web: ['On the web version: YouTube links only, through free mirror servers (they are sometimes slow or down). Other sites need the Android or desktop app.', 'في نسخة الويب: روابط يوتيوب فقط، عبر خوادم وسيطة مجانية (تكون أحيانًا بطيئة أو معطّلة). المواقع الأخرى تحتاج تطبيق الأندرويد أو الكمبيوتر.'],
  choose_files: ['Choose from device', 'اختر من الجهاز'], drop: ['or drop files here', 'أو اسحب الملفات هنا'],
  into_folder: ['Save in folder', 'احفظ في مجلد'], uploading: ['Uploading… {0}%', 'جارٍ الرفع… {0}٪'],
  added: ['Added ✓', 'أُضيف ✓'], no_links: ['Paste a link first', 'الصق رابطًا أولًا'], choose_first: ['Choose files first', 'اختر الملفات أولًا'], too_big_web: ['“{0}” is {1}. The web version keeps files inside the browser, so it can take up to about {2} per file. For a bigger lesson use the Android or desktop app, or make an audio-only (MP3) copy first.', '«{0}» حجمه {1}. نسخة الويب تحفظ الملفات داخل المتصفح، فتقبل حتى نحو {2} للملف الواحد. للدرس الأكبر استخدم تطبيق الأندرويد أو الكمبيوتر، أو اصنع نسخة صوتية (MP3) أولًا.'],
  add_how: ['Save the link as', 'احفظ الرابط كـ'], as_video: ['🎬 Video file', '🎬 ملف مرئي'], as_audio: ['🎧 Audio file', '🎧 ملف صوتي'], as_link: ['🔗 Link only', '🔗 رابط فقط'],
  add_how_p: ['Downloading first makes playing, cutting and transcribing fast and offline.', 'التنزيل أولًا يجعل التشغيل والقصّ والتفريغ سريعًا ويعمل دون إنترنت.'],
  // item
  rename: ['Rename', 'إعادة تسمية'], move: ['Folder', 'المجلد'], source: ['Source', 'المصدر'], in_projects: ['Projects', 'المشاريع'],
  sec_marks: ['Parts & bookmarks', 'المقاطع والعلامات'], sec_tr: ['Transcript', 'التفريغ'], sec_ex: ['Titled excerpts', 'المقتطفات المعنونة'],
  sec_notes: ['Benefits & notes', 'الفوائد والملاحظات'], sec_files: ['Files', 'الملفات'], sec_tools: ['Tools', 'أدوات'],
  marks_empty: ['While it plays: 🔖 for a point, or 🟢 Start then 🔴 End for a part. They appear here.', 'أثناء التشغيل: 🔖 لعلامة، أو 🟢 بداية ثم 🔴 نهاية لمقطع. ستظهر هنا.'],
  untitled: ['Untitled', 'بدون اسم'], select_all: ['Select all', 'تحديد الكل'], selected_n: ['{0} selected', 'محدّد {0}'],
  mp3: ['MP3', 'MP3'], video: ['Video', 'مرئي'], transcribe: ['Transcribe', 'فرّغ'], to_project: ['Project', 'مشروع'],
  note: ['Note', 'ملاحظة'], note_ph: ['Write a note about this part…', 'اكتب ملاحظة عن هذا المقطع…'], set_end: ['End here', 'النهاية هنا'],
  edit_times: ['Edit times', 'تعديل الوقت'], start: ['Start', 'البداية'], end: ['End', 'النهاية'], use_now: ['Use current time', 'الوقت الحالي'],
  end_opt: ['End (optional)', 'النهاية (اختياري)'], time_fmt: ['Write like 1:05.25 or 1:02:30.5 — hundredths of a second are kept', 'اكتب مثل 1:05.25 أو 1:02:30.5 — تُحفظ أجزاء الثانية'],
  from_player: ['From the player', 'من المشغّل'], part_typed: ['New part by times', 'مقطع جديد بكتابة الوقت'], len: ['Length', 'المدة'],
  recut_files: ['Cut the ready files again with the new times', 'أعد قصّ الملفات الجاهزة بالوقت الجديد'],
  s_exact: ['Re-encode video parts (slow — only for old players)', 'إعادة ترميز المقاطع المرئية (بطيء — للمشغّلات القديمة فقط)'],
  s_exact_p: ['Off (recommended): video parts are made instantly and still start and end exactly at your times. Turn on only if an old device plays a few extra frames at the start.', 'مُطفأ (المستحسن): المقطع المرئي يُصنع فورًا، ويبدأ وينتهي في وقتك بالضبط. فعّله فقط إذا كان جهاز قديم يعرض ثوانيَ زائدة في بداية المقطع.'],
  v_clip: ['The part', 'المقطع الجاهز'], v_src: ['Whole lesson', 'الدرس كاملًا'],
  bad_time: ['Check the times', 'تحقّق من الأوقات'], del_mark_q: ['Delete this mark?', 'حذف هذه العلامة؟'],
  tr_empty: ['No transcript yet.', 'لا يوجد تفريغ بعد.'], tr_all: ['All (merged)', 'الكل (مدمج)'], follow: ['Follow', 'تتبّع'],
  edit: ['Edit', 'تعديل'], done_edit: ['Save edits', 'حفظ التعديل'], download: ['Download', 'تنزيل'],
  copy: ['Copy', 'نسخ'], copied: ['Copied ✓', 'نُسخ ✓'], pick_tr: ['Choose one transcript above to edit it', 'اختر تفريغًا واحدًا من الأعلى لتعديله'],
  del_tr_q: ['Delete this transcript from the list? (its .txt file stays)', 'حذف هذا التفريغ من القائمة؟ (يبقى ملفّ .txt)'],
  cut_text: ['Cut an excerpt', 'اقتطع جزءًا'], pick_first: ['Tap the FIRST sentence of the excerpt', 'اضغط أوّل جملة من الجزء'],
  pick_last: ['Now tap the LAST sentence', 'الآن اضغط آخر جملة'], new_ex: ['New excerpt', 'مقتطف جديد'], ex_title: ['Title', 'العنوان'],
  ex_title_ph: ['e.g. Types of patience', 'مثال: أنواع الصبر'], ex_saved: ['Excerpt saved ✓', 'حُفظ المقتطف ✓'], save_proj: ['Save + project', 'حفظ + مشروع'],
  ex_empty: ['Cut titled excerpts from the transcript (✂️ above). Titles also appear as headings in exported books.', 'اقتطع أجزاء معنونة من التفريغ (✂️ في الأعلى). تظهر العناوين أيضًا في الكتاب عند التصدير.'],
  del_ex_q: ['Delete this excerpt?', 'حذف هذا المقتطف؟'], more: ['More', 'المزيد'], less: ['Less', 'أقلّ'],
  add_note: ['Add a benefit', 'أضف فائدة'], note_text_ph: ['Write the benefit or your note…', 'اكتب الفائدة أو ملاحظتك…'],
  link_time: ['Link to current time', 'اربطها بالوقت الحالي'], notes_empty: ['Write benefits while you listen — each can be linked to its moment.', 'اكتب الفوائد أثناء الاستماع — ويمكن ربط كل فائدة بوقتها.'],
  del_note_q: ['Delete this note?', 'حذف هذه الملاحظة؟'], files_empty: ['No files yet.', 'لا توجد ملفات بعد.'],
  open: ['Open', 'فتح'], save_file: ['Save', 'حفظ'], open_folder: ['Open folder', 'افتح المجلد'], main_folder: ['Main', 'الرئيسي'],
  dl_audio: ['Download audio', 'تنزيل الصوت'], dl_video: ['Download video', 'تنزيل المرئي'], to_mp3: ['Convert to MP3', 'تحويل إلى MP3'],
  tr_full: ['Transcribe all', 'تفريغ كامل'], export_book: ['Download transcript', 'تنزيل التفريغ'], del_item: ['Delete', 'حذف'],
  del_item_q: ['Delete “{0}”?', 'حذف «{0}»؟'], del_files_too: ['Also delete its files (downloads, parts, transcripts)', 'احذف ملفاته أيضًا (التنزيلات والمقاطع والتفريغات)'],
  in_tasks: ['Added to Tasks — runs in the background', 'أُضيفت إلى المهام — تعمل في الخلفية'],
  getting_audio: ['Downloading the file…', 'جارٍ تنزيل الملف…'], reading_link: ['Reading the link…', 'قراءة الرابط…'],
  dl_banner: ['Downloading the {0} to the phone', 'جارٍ تنزيل {0} إلى الهاتف'], dl_banner_p: ['After it finishes: plays offline, in the background, and cuts instantly.', 'بعد اكتماله: يعمل دون إنترنت وفي الخلفية، والقصّ فوري.'],
  the_video: ['video', 'المرئي'], the_audio: ['audio', 'الصوت'], dl_done: ['✅ Download finished', '✅ اكتمل التنزيل'], busy_tr: ['Transcribing…', 'جارٍ التفريغ…'],
  yt_net: ['The YouTube player needs internet.', 'مشغّل يوتيوب يحتاج إنترنت.'], not_downloaded: ['Not downloaded yet', 'لم يُنزَّل بعد'],
  audio_only: ['Audio only', 'صوت فقط'], show_video: ['Show video', 'أظهر المرئي'], fullscreen: ['Full screen', 'ملء الشاشة'], speed: ['Speed', 'السرعة'],
  // dock
  bookmark: ['Mark', 'علامة'], start_btn: ['Start', 'بداية'], end_btn: ['End', 'نهاية'],
  not_ready: ['Player not ready yet', 'المشغّل لم يجهز بعد'], press_start: ['Press Start first', 'اضغط «بداية» أولًا'],
  end_after: ['End must be after the start', 'النهاية يجب أن تكون بعد البداية'], marked_at: ['🔖 Marked at {0}', '🔖 علامة عند {0}'],
  name_it: ['Name it', 'سمِّها'], new_part: ['New part', 'مقطع جديد'], part_name: ['Name (optional)', 'الاسم (اختياري)'],
  part_name_ph: ['e.g. The meaning of patience', 'مثال: معنى الصبر'], save_only: ['Save', 'حفظ'], save_mp3: ['Save + MP3', 'حفظ + MP3'],
  save_tr: ['Save + transcribe', 'حفظ + تفريغ'], part_saved: ['Part saved ✓', 'حُفظ المقطع ✓'],
  st_ready: ['ready', 'جاهز'], st_wait: ['waiting', 'في الانتظار'], retry_short: ['Retry', 'أعد'],
  // export
  exp_title: ['Title', 'العنوان'], exp_sub: ['Subtitle', 'العنوان الفرعي'], exp_author: ['Author / speaker', 'المؤلف / الشيخ'],
  exp_format: ['Format', 'الصيغة'], f_pdf: ['PDF book', 'كتاب PDF'], f_txt: ['Text (TXT)', 'نص TXT'], f_word: ['Word', 'Word'],
  exp_content: ['Content', 'المحتوى'], exp_full: ['Full', 'الكامل'], exp_parts: ['Parts', 'المقاطع'], exp_ex: ['Excerpts', 'المقتطفات'], exp_both: ['Full + parts', 'الكامل والمقاطع'],
  exp_times: ['Times', 'التوقيت'], with_ts: ['With times', 'مع التوقيت'], no_ts: ['Without', 'بدون توقيت'],
  exp_notes: ['Include benefits', 'تضمين الفوائد'], exp_cover: ['Cover page', 'صفحة غلاف'], exp_toc: ['Contents page', 'فهرس'],
  exp_style: ['Layout', 'التنسيق'], exp_paras: ['Paragraphs', 'فقرات'], exp_lines: ['Line by line', 'سطرًا سطرًا'], exp_size: ['Text size', 'حجم الخط'],
  small: ['Small', 'صغير'], medium: ['Medium', 'متوسط'], large: ['Large', 'كبير'], xlarge: ['X-large', 'كبير جدًا'], huge: ['Huge', 'ضخم'],
  exp_more: ['More options', 'خيارات أخرى'], exp_go: ['Download', 'تنزيل'], exp_go_pdf: ['Open & save as PDF', 'افتح واحفظ PDF'],
  preview: ['Preview', 'معاينة'], pdf_hint: ['On the print screen choose “Save as PDF”.', 'في شاشة الطباعة اختر «حفظ بتنسيق PDF».'],
  // search
  search_title: ['Search your lessons', 'ابحث في دروسك'], search_p: ['Find every place a topic is mentioned in all transcribed lessons. Separate similar words with a comma.', 'اعثر على كل موضع ذُكر فيه موضوع في كل الدروس المفرّغة. افصل الكلمات المتقاربة بفاصلة.'],
  search_ph: ['e.g. patience, trials', 'مثال: الصبر، الابتلاء'], everywhere: ['Everywhere', 'في كل المكتبة'], go: ['Search', 'بحث'],
  results_n: ['{0} places in {1} items', '{0} موضعًا في {1} عناصر'], no_results: ['No results. Try other words, or transcribe more items.', 'لا نتائج. جرّب كلمات أخرى أو فرّغ عناصر أكثر.'],
  untr_n: ['{0} items are not transcribed yet, so they are not searched.', '{0} عناصر لم تُفرَّغ بعد، فلا يُبحث فيها.'], tr_them: ['Transcribe them', 'فرّغها الآن'],
  listen: ['Listen', 'استمع'], add_all_proj: ['Add all to a project', 'أضف الكل إلى مشروع'], mark_here: ['Mark', 'علامة'], excerpt: ['Excerpt', 'مقتطف'],
  // folders
  tab_lessons: ['Lessons', 'الدروس'], tab_parts: ['Parts', 'المقاطع'], tab_ex: ['Excerpts', 'المقتطفات'],
  parts_empty: ['No parts here yet.', 'لا مقاطع هنا بعد.'], ex_empty_f: ['No excerpts here yet.', 'لا مقتطفات هنا بعد.'], dl_book_all: ['Download all as a book', 'نزّلها كلها ككتاب'],
  // projects
  proj_p: ['Group lessons, parts and excerpts about one topic, then download them in order with a book.', 'اجمع دروسًا ومقاطع عن موضوع واحد، ثم نزّلها مرتّبة مع كتاب.'],
  new_project: ['New project', 'مشروع جديد'], project_name: ['Project name', 'اسم المشروع'], clips_n: ['{0} clips', '{0} مقاطع'], lessons_n: ['{0} lessons', '{0} دروس'],
  proj_empty: ['No projects yet.', 'لا مشاريع بعد.'], proj_clips_empty: ['Add clips from Search, from a lesson’s parts, or from excerpts (💼+).', 'أضف مقاطع من البحث، أو من مقاطع أي درس، أو من المقتطفات (💼+).'],
  proj_lessons: ['Lessons in this project', 'دروس المشروع'], proj_clips: ['Clips', 'المقاطع'], add_lessons: ['Add lessons', 'أضف دروسًا'],
  description: ['Description', 'الوصف'], desc_ph: ['What is this project about?', 'عن ماذا هذا المشروع؟'],
  dl_all_zip: ['Download all clips (ZIP)', 'نزّل كل المقاطع (ZIP)'], zip_ready: ['Ready — save the ZIP', 'جاهز — احفظ ملف ZIP'],
  choose_project: ['Project', 'المشروع'], clip_title: ['Clip title', 'عنوان المقطع'], added_to: ['Added to “{0}” ✓', 'أُضيف إلى «{0}» ✓'],
  del_proj_q: ['Delete this project? (the lessons are not touched)', 'حذف هذا المشروع؟ (الدروس لا تتأثّر)'], total: ['Total', 'المجموع'], done: ['Done', 'تمّ'],
  // tasks
  pause_all: ['Pause all', 'إيقاف الكل'], resume_all: ['Resume all', 'استئناف الكل'], clear_done: ['Clear finished', 'مسح المنتهية'],
  no_tasks: ['No tasks. Downloads and transcriptions appear here.', 'لا مهام. تظهر هنا التنزيلات والتفريغات.'],
  pause: ['Pause', 'إيقاف'], resume: ['Resume', 'استئناف'], retry: ['Retry', 'أعد المحاولة'], show: ['Show', 'عرض'],
  st_running: ['running', 'يعمل'], st_queued: ['waiting', 'ينتظر'], st_paused: ['paused', 'متوقّف'], st_error: ['error', 'خطأ'], st_done: ['done ✓', 'اكتمل ✓'], st_cancelled: ['cancelled', 'أُلغي'],
  // settings
  s_lang: ['Language', 'اللغة'], s_look: ['Appearance', 'المظهر'], s_theme: ['Theme', 'السمة'], auto: ['Auto', 'تلقائي'], light: ['Light', 'فاتح'], dark: ['Dark', 'داكن'], sepia: ['Paper', 'ورقي'],
  s_accent: ['Main color', 'اللون الرئيسي'], s_size: ['Text size', 'حجم الخط'], s_zoom: ['Display size (this device)', 'حجم الواجهة (لهذا الجهاز)'], z_auto: ['Fit screen', 'حسب الشاشة'], s_trsize: ['Transcript text size', 'حجم خط التفريغ'],
  s_tr: ['Transcription', 'التفريغ'], s_engine: ['Engine', 'المحرّك'], engine_groq: ['Groq — online, very fast and precise (free)', 'Groq — عبر الإنترنت، سريع ودقيق جدًا (مجاني)'],
  engine_local: ['Offline — on this device (much slower)', 'محلّي — على هذا الجهاز (أبطأ بكثير)'], s_key: ['Groq key', 'مفتاح Groq'],
  key_saved: ['Saved — paste a new one to replace', 'محفوظ — الصق مفتاحًا جديدًا للاستبدال'], key_hint: ['Free: console.groq.com/keys → sign in → Create API Key → paste here once.', 'مجانًا: console.groq.com/keys ← سجّل الدخول ← Create API Key ← الصقه هنا مرة واحدة.'],
  s_model: ['Model', 'النموذج'], model_best: ['whisper-large-v3 — most precise (recommended)', 'whisper-large-v3 — الأدقّ (مُوصى به)'], model_fast: ['whisper-large-v3-turbo — faster', 'whisper-large-v3-turbo — أسرع'],
  s_speech: ['Spoken language', 'لغة الكلام'], s_hint: ['Hint words (optional)', 'كلمات مساعدة (اختياري)'], hint_ph: ['Names and terms that appear often', 'أسماء ومصطلحات تتكرّر'],
  hint_p: ['Helps spell names and special terms correctly.', 'تساعد على كتابة الأسماء والمصطلحات بشكل صحيح.'],
  s_view: ['Display', 'العرض'], s_show_tr: ['Show the transcript under the player', 'إظهار التفريغ تحت المشغّل'], s_follow: ['Highlight and follow the spoken sentence', 'تمييز الجملة المسموعة وتتبّعها'],
  s_search: ['Clips from search', 'مقاطع البحث'], pad_before: ['Seconds before', 'ثوانٍ قبل'], pad_after: ['Seconds after', 'ثوانٍ بعد'],
  s_dl: ['Downloads', 'التنزيل'], s_md: ['Downloads at the same time', 'تنزيلات في نفس الوقت'], s_mt: ['Transcriptions at the same time', 'تفريغات في نفس الوقت'], s_quality: ['Video quality', 'جودة المرئي'],
  s_newlink: ['New links are saved as', 'الروابط الجديدة تُحفظ كـ'],
  s_update: ['Update', 'التحديث'], version: ['Version', 'الإصدار'], upd_find: ['Find update in Downloads', 'ابحث عن تحديث في التنزيلات'], upd_file: ['Choose update file (.zip)', 'اختر ملف التحديث (zip)'],
  upd_none: ['No Maqati zip found in Download. Download the new zip first.', 'لم يُعثر على ملف مقاطع في التنزيلات. نزّل الملف الجديد أولًا.'], upd_found: ['Found {0} (version {1})', 'وُجد {0} (الإصدار {1})'],
  upd_install: ['Install update', 'ثبّت التحديث'], upd_wait: ['Updating… the app restarts by itself', 'جارٍ التحديث… سيُعاد التشغيل تلقائيًا'], upd_done: ['Updated to {0} ✓', 'تمّ التحديث إلى {0} ✓'],
  upd_ytdlp: ['Update YouTube downloader', 'تحديث أداة تنزيل يوتيوب'], s_status: ['Status', 'الحالة'], files_at: ['Your files are in:', 'ملفاتك في:'],
  saved: ['Saved ✓', 'حُفظ ✓'], test_tr: ['Test transcription now', 'اختبر التفريغ الآن'], yes: ['Yes', 'نعم'], ok: ['OK', 'حسنًا'],
  done_lock: ['Done', 'مُنجز'], lock_ok: ['Confirm: done & lock', 'تأكيد: مُنجز وقفل'], unlock_ok: ['Confirm: unlock', 'تأكيد: فتح للتعديل'],
  locked_msg: ['Done & locked — tap ✓ on the part to unlock', 'مُنجز ومقفل — اضغط ✓ عند المقطع لفتحه'],
  tr_choose: ['Choose a transcript', 'اختر التفريغ'], tr_showing: ['Showing', 'المعروض'], tr_search_ph: ['Search in the transcript…', 'ابحث في التفريغ…'], tr_hits: ['{0} matches · tap one to jump there', '{0} نتيجة · اضغط أيّها لينتقل التشغيل إليها'], tr_nohit: ['No match', 'لا نتيجة'],
  pin: ['Pin', 'تثبيت'], pinned: ['Pinned', 'مثبّت'], working_on: ['Working on now', 'قيد العمل الآن'],
  continue: ['Continue listening', 'أكمل الاستماع'],
  more_opts: ['More', 'المزيد'], my_works: ['My works', 'أعمالي'], my_works_s: ['Cuts & transcripts', 'المقاطع والتفريغات'],
  works_all_p: ['Every cut and transcript from all your lessons. Choose a folder or a type; tap one to play, save, rename, re-cut or add it to a project.', 'كل مقاطعك وتفريغاتك من كل الدروس. اختر مجلدًا أو نوعًا، واضغط أيًّا منها للتشغيل أو الحفظ أو إعادة التسمية أو القص أو إضافته لمشروع.'],
  imp_found: ['Your {0} lessons from the old version ({1}) are still in Termux', 'دروسك القديمة ({0} درسًا) من النسخة {1} ما زالت في Termux'],
  imp_p: ['Bring them here: parts, transcripts, notes and projects. Keep Termux until this is done.', 'انقلها إلى هنا بضغطة: المقاطع والتفريغات والفوائد والمشاريع. لا تحذف Termux قبل ذلك.'],
  imp_noshare: ['First allow “All files” for Maqati in the phone settings, so the old files can be found.', 'اسمح أولًا لـ«مقاطع» بالوصول إلى جميع الملفات من إعدادات الهاتف، حتى تُوجد ملفاتك القديمة.'],
  imp_go: ['Bring them', 'انقلها'], imp_busy: ['Bringing your lessons… {0} of {1}', 'ينقل دروسك… {0} من {1}'],
  imp_done: ['{0} lessons brought over. You can now remove Termux and the old app.', 'نُقل {0} درسًا. يمكنك الآن حذف Termux والتطبيق القديم.'],
  t_now: ['Now', 'الحالية'], t_done: ['Finished', 'المنجزة'], no_done: ['Finished tasks appear here.', 'تظهر هنا المهام المنجزة.'],
  rmd_next: ['Next reminder', 'التذكير التالي'], s_rmd: ['Verses and hadiths banner (tap it for the next)', 'شريط الآيات والأحاديث (اضغطه للتالي)'], unlock_s: ['Unlock', 'فتح القفل'], unpin: ['Unpin', 'إلغاء التثبيت'], select: ['Select', 'تحديد'], note: ['Note', 'ملاحظة'], speed: ['Speed', 'السرعة'],
  sec_marks_s: ['Parts', 'المقاطع'], sec_tr_s: ['Transcript', 'التفريغ'], sec_notes_s: ['Benefits', 'الفوائد'], sec_files_s: ['Files', 'الملفات'],
  lan_t: ['Open from an iPhone or another device', 'فتح من الآيفون أو جهاز آخر'],
  lan_p: ['Use Maqati from an iPhone, tablet or computer on the same Wi-Fi. Everything works, downloads too: this phone does the work.', 'استعمل «مقاطع» من آيفون أو تابلت أو كمبيوتر على نفس شبكة الواي فاي. كل شيء يعمل حتى التحميل: هذا الهاتف يقوم بالعمل.'],
  lan_sw: ['Allow devices on my Wi-Fi', 'السماح للأجهزة على شبكتي'],
  lan_code: ['Code (type it once on the other device)', 'الرمز (يُكتب مرة واحدة في الجهاز الآخر)'],
  lan_new: ['New code', 'رمز جديد'],
  lan_nowifi: ['Connect this phone to Wi-Fi first.', 'وصّل هذا الهاتف بالواي فاي أولًا.'],
  lan_steps: ['Both devices on the same Wi-Fi.|On the iPhone open the Camera and point it at the code above, then tap the link (or type the address in Safari).|Type the code.|In Safari tap Share, then “Add to Home Screen”: Maqati gets its own icon.|Keep this phone on and Maqati running.', 'الجهازان على نفس شبكة الواي فاي.|في الآيفون افتح الكاميرا ووجّهها إلى المربع أعلاه ثم اضغط الرابط (أو اكتب العنوان في Safari).|اكتب الرمز.|في Safari اضغط «مشاركة» ثم «إضافة إلى الشاشة الرئيسية»: يصير لـ«مقاطع» أيقونة.|اترك هذا الهاتف مشغّلًا و«مقاطع» يعمل.'], play: ['Play', 'تشغيل'], settings_btn: ['Settings', 'الإعدادات'],
  tab_works: ['Works', 'الأعمال'], works_p: ['Everything made in this folder is gathered here automatically — tap any one to use it.', 'كل ما عُمل في هذا المجلد يُجمع هنا تلقائيًّا — اضغط أيّها لتعمل عليه.'],
  w_all: ['All', 'الكل'], w_tr: ['Transcripts', 'تفريغات'], w_audio: ['Audio', 'صوتيات'], w_video: ['Video', 'مرئيات'], works_empty: ['Nothing made here yet', 'لا توجد أعمال هنا بعد'],
  exp_font: ['Font', 'الخط'], exp_hfont: ['Headings font', 'خط العناوين'], edit_paras: ['Paragraphs: names & times', 'الفقرات: الأسماء والتوقيت'],
  paras_p: ['Each paragraph: a title (optional), its start and end. A deleted paragraph is left out of the file.', 'لكل فقرة عنوان (اختياري) وبداية ونهاية. الفقرة المحذوفة لا تدخل في الملف.'],
  add_para: ['Add paragraph', 'فقرة جديدة'], paras_auto: ['Back to automatic', 'رجوع للتقسيم التلقائي'], para_title_ph: ['Paragraph title (optional)', 'عنوان الفقرة (اختياري)'],
  paras_own: ['✓ Your paragraphs are used', '✓ تُستخدم فقراتك المعدّلة'],
  s_fonts: ['Fonts', 'الخطوط'], f_ui: ['App', 'الموقع'], f_head: ['Headings', 'العناوين'], f_read: ['Content & transcripts', 'المحتوى والتفريغ'],
  s_dhikr: ['Reminder', 'التذكير'], dhikr_p: ['“لا حول ولا قوة إلا بالله” shows small in the corner for 3 seconds.', 'تظهر «لا حول ولا قوة إلا بالله» بخط صغير في الركن ٣ ثوانٍ.'],
  off: ['Off', 'إيقاف'], m10: ['Every 10 min', 'كل ١٠ دقائق'], m15: ['Every 15 min', 'كل ربع ساعة'],
  quality: ['Quality', 'الجودة'], q_orig: ['Original', 'الأصلية'], q_best_a: ['highest', 'أعلى جودة'], q_small: ['smallest file', 'أصغر حجمًا'],
  q_reading: ['Reading the qualities…', 'يقرأ الجودات المتاحة…'], q_default: ['As in settings ({0})', 'حسب الإعدادات ({0})'],
  new_sub: ['New sub-folder', 'مجلد فرعي جديد'], no_sub: ['No sub-folder', 'بلا مجلد فرعي'], sub_ph: ['e.g. Chapter 1', 'مثال: الفصل الأول'],
  sub_empty: ['Empty — move clips here with 📁', 'فارغ — انقل المقاطع إليه بزرّ 📁'], move_to_sub: ['Move to sub-folder', 'نقل إلى مجلد فرعي'],
  sub_opt: ['Sub-folder (optional)', 'مجلد فرعي (اختياري)'], del_sub_q: ['Delete sub-folder “{0}”? Its clips stay in the project.', 'حذف المجلد الفرعي «{0}»؟ تبقى مقاطعه في المشروع.'],
  clip_win: ['Part', 'المقطع'], recut: ['Cut again with these times', 'أعد القصّ بهذا الوقت'], in_lesson: ['Open in lesson', 'افتحه في الدرس'],
  del_file: ['Delete this file', 'احذف هذا الملف'], del_file_q: ['Delete this file?', 'حذف هذا الملف؟'], skip_by: ['Jump', 'التقديم والتأخير'], test_mirrors: ['Test backup servers', 'اختبر الخوادم البديلة'], test_yt: ['Test YouTube now', 'اختبر يوتيوب الآن'], mir_ok: ['{0} of {1} servers work — downloads can use them if YouTube blocks you.', 'يعمل {0} من {1} — سيستعملها التطبيق وحده إذا حظرك يوتيوب.'], mir_none: ['No backup server answers right now. Fastest fix: turn on the free 1.1.1.1 (WARP) app and retry, or add a cookies file.', 'لا يوجد خادم بديل يعمل الآن. الحل الأسرع: ثبّت تطبيق 1.1.1.1 (WARP) المجاني وشغّله ثم أعد المحاولة، أو أضف ملف الكوكيز.'],
  left: ['~{0} left', 'يتبقّى ~{0}'], took: ['took {0}', 'استغرق {0}'],
  s_yt: ['YouTube', 'يوتيوب'], ck_on: ['YouTube cookies added ✓', 'ملف كوكيز يوتيوب مُضاف ✓'], ck_off: ['No cookies file', 'لا يوجد ملف كوكيز'],
  ck_add: ['Add cookies.txt', 'أضف ملف cookies.txt'], ck_del: ['Remove', 'احذفه'],
  ck_p: ['Only needed if YouTube says “confirm you’re not a bot”. Fastest fix: install the free 1.1.1.1 (WARP) app, turn it on, and press Retry. If it still happens: on the phone install the Quetta browser, add the extension “Get cookies.txt LOCALLY” from the Chrome Web Store, open youtube.com signed in, export cookies.txt and add it here.', 'يُحتاج فقط إذا قال يوتيوب «أكّد أنك لست روبوتًا». الحل الأسرع: ثبّت تطبيق 1.1.1.1 (WARP) المجاني وشغّله ثم اضغط «أعد المحاولة». إن استمرّ: ثبّت متصفح Quetta على الهاتف، وأضف إليه إضافة «Get cookies.txt LOCALLY» من متجر Chrome، وافتح youtube.com وأنت مسجّل الدخول، وصدّر ملف cookies.txt وأضفه هنا.'],
  key_tip: ['Tip: add your free Groq key in Settings to transcribe', 'تلميح: أضف مفتاح Groq المجاني من الإعدادات للتفريغ'],
};
let LANG = 'ar';
const t = (k, ...a) => { let s = (TX[k] || [k, k])[LANG === 'ar' ? 1 : 0]; a.forEach((v, i) => s = s.replace('{' + i + '}', v)); return s; };

/* ================= helpers ================= */
async function api(path, opts = {}) {
  const o = { ...opts };
  if (o.body && !(o.body instanceof Blob)) { o.headers = { 'Content-Type': 'application/json' }; o.body = JSON.stringify(o.body); }
  const r = await fetch(path, o);
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail || m; } catch (e) {} throw new Error(m); }
  return r.json();
}
const post = (p, b) => api(p, { method: 'POST', body: b || {} });
const patch = (p, b) => api(p, { method: 'PATCH', body: b });
const del = p => api(p, { method: 'DELETE' });
function fmt(x) {
  if (x == null || isNaN(x) || !isFinite(x)) return '0:00';
  x = Math.max(0, x); const h = Math.floor(x / 3600), m = Math.floor(x % 3600 / 60), s = Math.floor(x % 60);
  return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(s).padStart(2, '0');
}
/* times with hundredths of a second: 1:05.37 */
function fmtP(x) {
  if (x == null || isNaN(x) || !isFinite(x)) return '';
  const cs = Math.round(Math.max(0, x) * 100), s = Math.floor(cs / 100), f = cs % 100;
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60);
  return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(s % 60).padStart(2, '0') + '.' + String(f).padStart(2, '0');
}
/* short form: whole seconds, plus tenths when the time has them */
function fmtS(x) { if (x == null || isNaN(x)) return fmt(x); const d = Math.round(x * 10) % 10; return d ? fmtP(Math.round(x * 10) / 10).slice(0, -1) : fmt(Math.round(x)); }
function parseT(v) {
  v = String(v || '').trim().replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d)).replace(/[٫,]/g, '.').replace(/[؛;]/g, ':'); if (!v) return null;
  const p = v.split(':').map(Number); if (p.some(isNaN)) return undefined;
  return p.reduce((a, x) => a * 60 + x, 0);
}
const rng = (a, b) => `<bdi dir="ltr">${fmtS(a)} – ${fmtS(b)}</bdi>`;
const SEP = () => LANG === 'ar' ? '‹' : '›';
const size = b => b > 1e9 ? (b / 1e9).toFixed(1) + ' GB' : b > 1e6 ? (b / 1e6).toFixed(1) + ' MB' : Math.max(1, Math.ceil(b / 1e3)) + ' KB';
const dur = x => x == null ? '' : x < 60 ? (LANG === 'ar' ? `${Math.max(1, Math.round(x))} ث` : `${Math.max(1, Math.round(x))}s`) : fmt(x);
const leftTxt = j => j && j.eta ? t('left', dur(j.eta)) : '';
const tookTxt = j => j && j.taken ? t('took', dur(j.taken)) : '';
const mediaURL = p => '/media/' + encURI(p);
const nice = s => String(s || '').replace(/(?:من\s*)?(\d{1,2}(?:-\d{2}){1,2})\s*(?:إلى|to|–|→)\s*(\d{1,2}(?:-\d{2}){1,2}|النهاية|end)/g, (m, a, b) => `${a.replace(/-/g, ':')} – ${b.replace(/-/g, ':')}`).replace(/\s*\[(audio|video)\]/gi, '').replace(/\s*\(\d+\)\s*$/, '').trim();

let toastT;
function toast(msg, action, ms = 3000) {
  const el = $('#toast'); el.innerHTML = `<span>${esc(msg)}</span>` + (action ? `<button>${esc(action.label)}</button>` : '');
  el.hidden = false; if (action) $('button', el).onclick = () => { el.hidden = true; action.fn(); };
  clearTimeout(toastT); toastT = setTimeout(() => el.hidden = true, action ? 6000 : ms);
}
function copy(txt) { navigator.clipboard.writeText(txt).then(() => toast(t('copied')), () => toast('✗')); }
function download(url) { const a = document.createElement('a'); a.href = url; a.download = ''; document.body.appendChild(a); a.click(); a.remove(); }

/* ---------- sheets (bottom sheet on phones, dialog on bigger screens) ---------- */
function sheet(title, body, foot, onOpen) {
  const d = $('#sheet');
  d.innerHTML = `<div class="grab"></div><div class="sh"><b>${title}</b><button class="ib" value="x" aria-label="close">✕</button></div>
    <div class="sb">${body}</div>${foot ? `<div class="sf">${foot}</div>` : ''}`;
  if (!d.open) d.showModal();
  return new Promise(res => {
    const close = v => { if (d.open) d.close(); res(v); };
    d.onclick = e => { const b = e.target.closest('button[value]'); if (b) close(b.value); else if (e.target === d) close(null); };
    d.oncancel = () => res(null);
    if (onOpen) onOpen(d, close);
  });
}
async function ask(msg, okLabel, danger) {
  return (await sheet(esc(msg), '', `<button class="btn big" value="no">${t('cancel')}</button><button class="btn big ${danger ? 'danger-fill' : 'pri'}" value="yes">${okLabel || t('yes')}</button>`)) === 'yes';
}
async function promptText(title, value, ph) {
  let val = value || '';
  const r = await sheet(esc(title), `<div class="field"><input id="pt" dir="auto" value="${esc(val)}" placeholder="${esc(ph || '')}"></div>`,
    `<button class="btn big" value="no">${t('cancel')}</button><button class="btn big pri" value="ok">${t('save')}</button>`, d => {
      const i = $('#pt', d); setTimeout(() => { i.focus(); i.select(); }, 60);
      i.oninput = () => val = i.value;
      i.onkeydown = e => { if (e.key === 'Enter') { val = i.value; $('button[value=ok]', d).click(); } };
    });
  return r === 'ok' ? val.trim() : null;
}
const segc = (name, val, opts, attr = 'data-seg') => `<div class="segc" ${attr}="${name}">${opts.map(([v, l]) => `<button type="button" data-v="${v}" class="${String(val) === String(v) ? 'on' : ''}">${l}</button>`).join('')}</div>`;
function wireSegc(root, cb) { $$('[data-seg]', root).forEach(g => $$('button', g).forEach(b => b.onclick = e => { e.stopPropagation(); $$('button', g).forEach(x => x.classList.toggle('on', x === b)); cb(g.dataset.seg, b.dataset.v); })); }

/* ================= state ================= */
const S = { set: {}, folders: [], items: [], jobs: [], item: null, tr: { key: null, segs: [] }, pending: null, sel: new Set(), editTr: false, q: '', res: null, pick: null };
async function loadSettings() { S.set = await api('/api/settings'); LANG = S.set.lang === 'en' ? 'en' : 'ar'; applyLook(); }
function applyLook() {
  const r = document.documentElement, s = S.set;
  r.lang = LANG; r.dir = LANG === 'ar' ? 'rtl' : 'ltr';
  r.dataset.theme = s.theme || 'auto';
  if (OLD_COLORS[s.accent]) s.accent = OLD_COLORS[s.accent];
  if (!COLORS.includes(s.accent)) s.accent = COLORS[0];
  const dark = s.theme === 'dark' || (s.theme !== 'light' && s.theme !== 'sepia' && matchMedia('(prefers-color-scheme: dark)').matches);
  r.classList.toggle('isdark', dark);
  const fu = FONTS[s.font_ui] || FONTS.tajawal, fh = FONTS[s.font_head] || fu;
  r.style.setProperty('--ui', fstack(s.font_ui)); r.style.setProperty('--head', fstack(s.font_head || s.font_ui)); r.style.setProperty('--read', fstack(s.font_read || 'amiri'));
  r.style.setProperty('--wb', fu[3]); r.style.setProperty('--wn', fu[5]); r.style.setProperty('--wh', fh[4]);
  // on a dark background the same colour is lifted, so text and icons in it stay easy to read
  r.style.setProperty('--acc', dark ? `color-mix(in srgb, ${s.accent} 55%, #ffffff)` : s.accent);
  r.style.setProperty('--acc-ink', dark ? '#0E1513' : '#ffffff');
  r.style.setProperty('--acc-deep', `color-mix(in srgb, ${s.accent} ${dark ? 62 : 82}%, #061412)`);   // solid fills with white text
  r.style.setProperty('--scale', s.font_scale || 1);
  fitZoom();
  r.style.setProperty('--trs', s.tr_scale || 1);
  $('meta[name=theme-color]').content = dark ? '#0E1513' : '#F6F3EC';
  const tb = $('#themeBtn'); if (tb) { tb.innerHTML = ICON(dark ? 'sun' : 'moon'); tb.setAttribute('aria-label', t(dark ? 'light' : 'dark')); }
  document.title = t('app'); $('#appName').textContent = t('app'); $('#appSub').textContent = t('tagline');
  $('#backBtn').innerHTML = ICON(LANG === 'ar' ? 'chevR' : 'chevL');
  renderTabs();
}
/* the whole page bigger or smaller, chosen per device: phones as designed, wide computer screens larger */
function fitZoom() {
  const z = store.get('zoom', 'auto');
  const v = z === 'auto' ? 1 : +z || 1;
  document.body.style.zoom = v === 1 ? '' : v;
}
window.addEventListener('resize', () => fitZoom());
async function loadLib() { const st = await api('/api/state'); S.folders = st.folders; S.items = st.items; }

/* ================= router ================= */
const ROUTES = [
  [/^#\/home$/, () => vHome()], [/^#\/lib$/, () => vLibrary()], [/^#\/lib\/f\/(\w+)(?:\/(\w+))?$/, m => vFolder(m[1], m[2])], [/^#\/item\/(\d+)(?:\/(\d+(?:\.\d+)?))?$/, m => vItem(+m[1], m[2] ? +m[2] : null)],
  [/^#\/search$/, () => vSearch()], [/^#\/projects$/, () => vProjects()], [/^#\/project\/(\d+)$/, m => vProject(+m[1])],
  [/^#\/tasks(?:\/(\w+))?$/, m => vTasks(m[1])], [/^#\/works$/, () => vFolder('all', 'works', true)], [/^#\/settings$/, () => vSettings()], [/^#\/help$/, () => vHelp()],
];
async function route() {
  const h = location.hash || '#/home';
  if (!/^#\/item\//.test(h)) leaveItemPage();
  S.pick = null;
  const hit = ROUTES.find(([rx]) => rx.test(h));
  if (!hit) { location.hash = '#/home'; return; }
  const v = view(); if (!pollJobs.busy) { v.classList.remove('enter'); void v.offsetWidth; v.classList.add('enter'); }
  clearTimeout(route.t); route.t = setTimeout(() => v.classList.remove('enter'), 900);
  await hit[1](h.match(hit[0]));
  $('#backBtn').hidden = !/^#\/(lib\/f|item|project\/|help|works|tasks|settings)/.test(h);
  renderTabs(); PL.place(); placeReminder();
}
window.addEventListener('hashchange', () => { route().then(() => window.scrollTo(0, 0)); });
window.addEventListener('scroll', () => $('.top').classList.toggle('scrolled', window.scrollY > 4), { passive: true });
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (S.set.theme === 'auto' || !S.set.theme) applyLook(); });
function renderTabs() {
  const h = location.hash || '#/home';
  const on = /^#\/home/.test(h) ? 'home' : /^#\/works/.test(h) ? 'works' : /^#\/(lib|item)/.test(h) ? 'lib' : /^#\/search/.test(h) ? 'search' : /^#\/project/.test(h) ? 'projects'
    : /^#\/tasks/.test(h) ? 'tasks' : /^#\/(settings|help)/.test(h) ? 'settings' : '';
  const active = S.jobs.filter(j => j.status === 'running' || j.status === 'queued').length;
  const tab = ([k, i, n, x]) => `<a href="#/${k}" class="${on === k ? 'on' : ''}${x ? ' x' : ''}"><i>${ICON(i)}</i><span>${t(n)}</span>${k === 'tasks' && active ? `<span class="badge">${active}</span>` : ''}</a>`;
  const mb = $('#menuBtn'); if (mb && !mb.innerHTML) { mb.innerHTML = ICON('list'); mb.setAttribute('aria-label', t('menu')); }
  const tb = $('#tasksBtn');
  if (tb) { tb.innerHTML = `${ICON('clock')}${active ? `<span class="badge">${active}</span>` : ''}`; tb.classList.toggle('busy', !!active); tb.setAttribute('aria-label', t('tasks')); }
  const sig = on + '|' + active + '|' + LANG;
  if ($('#tabbar').dataset.sig === sig) return;
  $('#tabbar').dataset.sig = sig;
  $('#tabbar').innerHTML = [['home', 'sparkle', 'home'], ['lib', 'library', 'library']].map(tab).join('')
    + `<button class="tadd" data-act="add" aria-label="${t('add')}">${ICON('plus')}<span>${t('add')}</span></button>`
    + [['search', 'search', 'search'], ['projects', 'case', 'projects']].map(tab).join('')
    + `<span class="xsep"></span>` + [['tasks', 'clock', 'tasks', 1], ['works', 'box', 'my_works', 1], ['settings', 'gear', 'settings', 1]].map(tab).join('');
}
const view = () => $('#view');

/* ================= the player: one, always alive, floats between pages ================= */
const PL = {
  item: null, el: null, kind: null, yp: null, audioOnly: false, autoAudio: false, rateV: 1,
  ready() { return !!(this.el || this.yp); },
  time() { return this.yp ? (this.yp.getCurrentTime ? this.yp.getCurrentTime() || 0 : 0) : this.el ? this.el.currentTime || 0 : 0; },
  dur() { const d = this.yp ? (this.yp.getDuration ? this.yp.getDuration() : 0) : this.el ? this.el.duration : 0; return isFinite(d) && d ? d : (this.item && this.item.duration) || 0; },
  playing() { return this.yp ? (this.yp.getPlayerState && this.yp.getPlayerState() === 1) : this.el ? !this.el.paused : false; },
  play() { if (this.yp) this.yp.playVideo(); else if (this.el) this.el.play().catch(() => {}); },
  pause() { if (this.yp) this.yp.pauseVideo(); else if (this.el) this.el.pause(); },
  toggle() { this.playing() ? this.pause() : this.play(); },
  seek(x, play = true) { x = Math.max(0, x); if (this.yp) { this.yp.seekTo(x, true); if (play) this.yp.playVideo(); } else if (this.el) { this.el.currentTime = x; if (play) this.play(); } },
  skip(d) { this.seek(Math.min(this.time() + d, this.dur() || 1e9), this.playing()); },
  rate(r) { this.rateV = r; if (this.yp) this.yp.setPlaybackRate(r); else if (this.el) this.el.playbackRate = r; },
  isVideoFile(item) { return item && item.file && item.media === 'video'; },
  load(item, at, autoplay) {
    if (item && /^\d+$/.test(String(item.id))) store.set('last', item.id);
    if (this.item && this.item.id === item.id && this.item.file === item.file && this.ready()) {
      this.item = item; if (at != null) this.seek(at, true); return;
    }
    this.unload();
    this.item = item; S.pending = null;
    const resume = at != null ? at : store.get('pos.' + item.id, 0);
    if (item.file) {
      this.makeEl(this.isVideoFile(item) && !this.audioOnly ? 'video' : 'audio', resume, autoplay || at != null);
    } else if (ytId(item.url)) {
      this.kind = 'yt';
    }
    this.session();
  },
  makeEl(kind, at, autoplay) {
    const old = this.el;
    const el = document.createElement(kind);
    el.preload = 'metadata'; el.src = mediaURL(this.item.file); el.setAttribute('playsinline', '');
    el.playbackRate = this.rateV;
    el.addEventListener('loadedmetadata', () => { if (at) el.currentTime = at; if (autoplay) el.play().catch(() => {}); }, { once: true });
    el.addEventListener('play', () => { ui(); if (window.MaqatiApp && MaqatiApp.playing) MaqatiApp.playing(true); });
    el.addEventListener('pause', () => { ui(); if (window.MaqatiApp && MaqatiApp.playing) MaqatiApp.playing(false); });
    el.addEventListener('ended', () => { if (window.MaqatiApp && MaqatiApp.playing) MaqatiApp.playing(false); });
    /* tap = play/pause; double-tap on the right/left side = forward/back (like YouTube) */
    let tapT = null, tapAt = 0;
    el.addEventListener('click', e => {
      const r = el.getBoundingClientRect(), side = (e.clientX - r.left) / r.width, now = Date.now();
      if (now - tapAt < 320) { clearTimeout(tapT); tapAt = 0; if (side > .6 || side < .4) { const f = side > .6; this.skip((f ? 1 : -1) * skipS()); skipFlash(el, f); } else this.toggle(); return; }
      tapAt = now; tapT = setTimeout(() => this.toggle(), 320);
    });
    this.el = el; this.kind = kind;
    if (old) { old.pause(); old.remove(); }
    $('#stage').appendChild(el);
    this.place();
  },
  setAudioOnly(on, auto) {
    if (!this.item || !this.isVideoFile(this.item)) return;
    this.audioOnly = on; this.autoAudio = !!auto;
    const at = this.time(), was = this.playing();
    this.makeEl(on ? 'audio' : 'video', at, was);
    ui();
  },
  unload() {
    if (this.el) { store.set('pos.' + this.item.id, this.el.currentTime || 0); this.el.pause(); this.el.remove(); }
    if (this.yp) { try { this.yp.destroy(); } catch (e) {} }
    this.el = null; this.yp = null; this.kind = null; this.item = null; this.audioOnly = false;
    $('#floatBox').hidden = true; ui();
  },
  mountYT(slot, at) {
    slot.innerHTML = '<div class="yt"><div id="ytp"></div></div>';
    loadYT().then(() => {
      if (!$('#ytp') || this.kind !== 'yt') return;
      this.yp = new YT.Player('ytp', { videoId: ytId(this.item.url), playerVars: { rel: 0, playsinline: 1, start: Math.floor(at || 0) },
        events: { onStateChange: () => ui() } });
    });
  },
  /* put the video where it belongs: in the lesson page, or in the small floating window */
  place() {
    const slot = $('#player'), onPage = slot && S.item && this.item && S.item.id === this.item.id;
    const fb = $('#floatBox');
    if (this.el && this.kind === 'video') {
      if (onPage) { if (this.el.parentElement !== slot) { slot.innerHTML = ''; slot.appendChild(this.el); } fb.hidden = true; }
      else { const box = $('#floatVid'); if (this.el.parentElement !== box) box.appendChild(this.el); fb.hidden = false; }
    } else {
      fb.hidden = true;
      if (this.el && this.el.parentElement !== $('#stage')) $('#stage').appendChild(this.el);
    }
    if (onPage && this.kind !== 'video') renderAudioArt(slot);
    ui();
  },
  session() {
    if (!('mediaSession' in navigator) || !this.item) return;
    try {
      navigator.mediaSession.metadata = new MediaMetadata({ title: nice(this.item.title), artist: t('app'),
        artwork: [{ src: this.item.thumb || '/static/icon-512.png', sizes: '512x512' }] });
      navigator.mediaSession.setActionHandler('play', () => this.play());
      navigator.mediaSession.setActionHandler('pause', () => this.pause());
      navigator.mediaSession.setActionHandler('seekbackward', () => this.skip(-skipS()));
      navigator.mediaSession.setActionHandler('seekforward', () => this.skip(skipS()));
      navigator.mediaSession.setActionHandler('seekto', d => this.seek(d.seekTime, this.playing()));
    } catch (e) {}
  },
};
let ytReady = null;
function loadYT() {
  if (ytReady) return ytReady;
  ytReady = new Promise(res => { window.onYouTubeIframeAPIReady = res; const s = document.createElement('script'); s.src = 'https://www.youtube.com/iframe_api'; s.onerror = () => toast(t('yt_net')); document.head.appendChild(s); });
  return ytReady;
}
const ytId = u => (String(u || '').match(/(?:v=|youtu\.be\/|shorts\/|embed\/|live\/)([\w-]{11})/) || [])[1];
function renderAudioArt(slot) {
  const it = PL.item;
  if (PL.kind === 'yt') { if (!$('#ytp', slot) && !$('.yt', slot)) PL.mountYT(slot, store.get('pos.' + it.id, 0)); return; }
  if (!it.file) { slot.innerHTML = `<div class="art"><i>⏳</i><b>${t('not_downloaded')}</b></div>`; return; }
  if (!$('.art', slot) || slot.dataset.for !== String(it.id) + PL.kind) {
    slot.dataset.for = String(it.id) + PL.kind;
    slot.innerHTML = `<div class="art" data-act="pp"><i>${PL.isVideoFile(it) ? '🎬' : '🎧'}</i><b dir="auto">${esc(nice(it.title))}</b></div>`;
  }
}
/* keep playing with the screen off / in another app: video switches to sound only while hidden */
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { if (PL.kind === 'video' && PL.playing()) PL.setAudioOnly(true, true); }
  else if (PL.autoAudio) PL.setAudioOnly(false);
});
setInterval(() => { if (PL.el && PL.item) store.set('pos.' + PL.item.id, PL.el.currentTime || 0); }, 5000);

/* ---------- player controls: the dock on the lesson page, the mini bar elsewhere ---------- */
const IC = {
  play: '<svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="currentColor" stroke="none"/></svg>',
  pause: '<svg viewBox="0 0 24 24"><rect x="6.5" y="5" width="4" height="14" rx="1.2" fill="currentColor" stroke="none"/><rect x="13.5" y="5" width="4" height="14" rx="1.2" fill="currentColor" stroke="none"/></svg>',
  back: '<svg viewBox="0 0 24 24"><path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1L3.5 8.5"/><path d="M3.5 3.5v5h5"/></svg>',
  fwd: '<svg viewBox="0 0 24 24"><path d="M20.5 12a8.5 8.5 0 1 1-2.6-6.1l2.6 2.6"/><path d="M20.5 3.5v5h-5"/></svg>',
  bm: '<svg viewBox="0 0 24 24"><path d="M6.5 3.5h11a1 1 0 0 1 1 1v16l-6.5-4.2-6.5 4.2v-16a1 1 0 0 1 1-1z"/></svg>',
  start: '<svg viewBox="0 0 24 24"><path d="M5 21V4"/><path d="M5 4h11l-2.5 4L16 12H5" fill="currentColor" fill-opacity=".25"/></svg>',
  end: '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2.5" fill="currentColor" fill-opacity=".25"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  dl: '<svg viewBox="0 0 24 24"><path d="M12 4v11"/><path d="M7 10.5 12 15.5 17 10.5"/><path d="M5 20h14"/></svg>',
  music: '<svg viewBox="0 0 24 24"><path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/></svg>',
  film: '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="14" rx="2.5"/><path d="M10 9.5v5l4-2.5z" fill="currentColor"/></svg>',
  doc: '<svg viewBox="0 0 24 24"><path d="M7 3.5h7l4 4v13H7z"/><path d="M14 3.5v4h4M9.5 12h6M9.5 15.5h6"/></svg>',
};
const PJADD = '<span class="pja">💼<i>+</i></span>';
/* the six fonts: key -> [css family, Arabic name, English name, bold weight, heading weight, normal weight, kind] */
const FONTS = { tajawal: ['Tajawal', 'تجوال', 'Tajawal', 500, 700, 400, 'm'], almarai: ['Almarai', 'المراعي', 'Almarai', 700, 700, 400, 'm'], plex: ['Plex', 'بلكس', 'IBM Plex', 600, 600, 400, 'm'],
  amiri: ['Amiri', 'أميري', 'Amiri', 700, 700, 400, 't'], naskh: ['Naskh', 'نسخ (مثل لوتس)', 'Naskh (Lotus-like)', 700, 700, 400, 't'], scheherazade: ['Scheherazade', 'شهرزاد (تقليدي)', 'Scheherazade', 700, 700, 400, 't'] };
const fstack = k => { const f = FONTS[k] || FONTS.tajawal; return `${f[0]},${f[6] === 't' ? '"Traditional Arabic",serif' : 'Tajawal,Plex,system-ui,sans-serif'}`; };
const fontSeg = (name, val, attr) => `<div class="segc fontseg" ${attr}="${name}">${Object.entries(FONTS).map(([k, f]) => `<button type="button" data-v="${k}" class="${val === k ? 'on' : ''}" style="font-family:${f[0]};font-weight:${f[5]}">${LANG === 'ar' ? f[1] : f[2]}</button>`).join('')}</div>`;
const skipS = () => store.get('skip', 5);
function skipFlash(el, fwd) {
  const host = el.parentElement; if (!host) return;
  const f = document.createElement('div'); f.className = 'skflash ' + (fwd ? 'r' : 'l'); f.innerHTML = (fwd ? IC.fwd : IC.back) + `<b>${skipS()}</b>`;
  host.appendChild(f); setTimeout(() => f.remove(), 600);
}
const ppIcon = () => PL.playing() ? IC.pause : IC.play;
/* the seek bar: a real track with the played part, the downloaded part, and every bookmark / part drawn on it */
const seekHTML = id => `<div class="sk" id="${id}" dir="ltr"><div class="trk"><i class="buf"></i><i class="fill"></i><div class="mks"></div></div><i class="knob"></i><b class="tip"></b></div>`;
function plMarks() {
  const it = PL.item; if (!it) return [];
  const src = S.item && S.item.id === it.id ? S.item : it;
  return (src.bookmarks || []);
}
function drawMarks(sk) {
  const d = PL.dur(), box = $('.mks', sk); if (!box) return;
  const ms = plMarks(), sig = d.toFixed(0) + '|' + ms.map(b => b.id + ':' + b.start + ':' + b.end).join(',') + '|' + (S.pending ?? '');
  if (box.dataset.sig === sig) return; box.dataset.sig = sig;
  if (!d) { box.innerHTML = ''; return; }
  const p = x => Math.min(100, Math.max(0, x / d * 100)).toFixed(3) + '%';
  box.innerHTML = ms.map(b => b.end != null
    ? `<i class="rg" style="left:${p(b.start)};width:calc(${p(b.end)} - ${p(b.start)})"></i><i class="pt" data-t="${b.start}" style="left:${p(b.start)}"></i>`
    : `<i class="pt bmk" data-t="${b.start}" style="left:${p(b.start)}"></i>`).join('')
    + (S.pending != null ? `<i class="pt live" style="left:${p(S.pending)}"></i>` : '');
}
function bindSeek(sk) {
  if (!sk || sk.dataset.bound) return; sk.dataset.bound = 1;
  const at = e => {
    const r = sk.getBoundingClientRect(), d = PL.dur(); let x = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)) * d;
    for (const b of plMarks()) if (Math.abs((b.start / d) * r.width - (e.clientX - r.left)) < 12) { x = b.start; break; }   // snap to a mark
    return x;
  };
  const show = x => { const d = PL.dur(); if (!d) return; sk.style.setProperty('--p', (x / d * 100) + '%'); $('.tip', sk).textContent = fmtP(x); const c = $('#dCur'); if (c) c.textContent = fmt(x); };
  sk.addEventListener('pointerdown', e => { if (!PL.dur()) return; seeking = sk; sk.classList.add('drag'); sk.setPointerCapture(e.pointerId); show(at(e)); e.preventDefault(); });
  sk.addEventListener('pointermove', e => { if (seeking === sk) show(at(e)); });
  const up = e => { if (seeking !== sk) return; const x = at(e); sk.classList.remove('drag'); seeking = null; PL.seek(x, PL.playing()); show(x); };
  sk.addEventListener('pointerup', up); sk.addEventListener('pointercancel', () => { sk.classList.remove('drag'); seeking = null; });
}
function ui() {
  const it = PL.item, onPage = it && S.item && S.item.id === it.id && /^#\/item\//.test(location.hash);
  const mini = $('#mini'), dock = $('#dock');
  mini.hidden = !it || onPage; dock.hidden = !onPage;
  document.documentElement.style.setProperty('--dock', onPage ? 'var(--dockh)' : it ? 'var(--minih)' : '0px');
  if (!mini.hidden && mini.dataset.for !== String(it.id) + '|' + it.title) {
    mini.dataset.for = String(it.id) + '|' + it.title;
    mini.innerHTML = `<div class="pcard">${seekHTML('miniSeek')}
      <div class="in"><button class="mthumb" data-act="go-playing" style="${it.thumb ? `background-image:url('${esc(it.thumb)}')` : ''}">${it.thumb ? '' : (PL.isVideoFile(it) || it.media === 'video' ? '🎬' : '🎧')}</button>
      <button class="mtitle" data-act="go-playing"><b dir="auto">${esc(nice(it.title))}</b><small id="miniTime" dir="ltr">0:00</small></button>
      <div class="ctl"><button class="ib" data-act="skip" data-s="-1">${IC.back}<em class="skn">${skipS()}</em></button><button class="ib play" data-act="pp" id="miniPP">${IC.play}</button>
      <button class="ib" data-act="skip" data-s="1">${IC.fwd}<em class="skn">${skipS()}</em></button></div><button class="ib x" data-act="pl-close">${IC.x}</button></div>
      ${false && plLesson() ? `<div class="mrow"><button class="mk main" data-act="bm">${IC.bm}<span>${t('bookmark')}</span></button>
        <button class="mk st" data-act="mstart" >${IC.start}<span>${t('start_btn')}</span></button>
        <button class="mk en" data-act="mend">${IC.end}<span>${t('end_btn')}</span></button></div>` : ''}</div>`;
    bindSeek($('#miniSeek'));
  }
  if (!dock.hidden && dock.dataset.for !== String(it.id) + '|' + it.title) {
    dock.dataset.for = String(it.id) + '|' + it.title;
    dock.innerHTML = `<div class="pcard"><div class="seekrow"><bdi id="dCur">0:00</bdi>${seekHTML('dockSeek')}<bdi id="dDur">0:00</bdi></div>
      <div class="btnrow">
        <div class="ctl"><button class="ib" data-act="skip" data-s="-1">${IC.back}<em class="skn">${skipS()}</em></button>
        <button class="ib play" data-act="pp" id="dockPP">${IC.play}</button>
        <button class="ib" data-act="skip" data-s="1">${IC.fwd}<em class="skn">${skipS()}</em></button></div>
        <span class="vsep"></span>
        <button class="mk main" data-act="bm">${IC.bm}<span>${t('bookmark')}</span></button>
        <button class="mk st" data-act="mstart" >${IC.start}<span>${t('start_btn')}</span></button>
        <button class="mk en" data-act="mend">${IC.end}<span>${t('end_btn')}</span></button>
      </div></div>`;
    bindSeek($('#dockSeek'));
  }
  paintPP();
  const tb = $('#pl-tools'); if (tb) tb.innerHTML = playerToolsHTML();
}
let seeking = null, lastPP = null;
function paintPP() { const p = PL.playing(); $$('#dockPP,#miniPP').forEach(b => { if (b.dataset.p !== String(p)) { b.dataset.p = p; b.innerHTML = p ? IC.pause : IC.play; } }); }
/* smooth: the bar follows the sound every frame; text and heavier work 4 times a second */
(function frame() {
  if (PL.item) {
    const x = PL.time(), d = PL.dur();
    $$('.sk').forEach(sk => {
      if (seeking !== sk) sk.style.setProperty('--p', (d ? Math.min(100, x / d * 100) : 0) + '%');
      const el = PL.el; if (el && d && el.buffered && el.buffered.length) sk.style.setProperty('--b', Math.min(100, el.buffered.end(el.buffered.length - 1) / d * 100) + '%');
    });
  }
  requestAnimationFrame(frame);
})();
setInterval(() => {
  if (!PL.item) return;
  const x = PL.time(), d = PL.dur();
  if (!seeking) { const c = $('#dCur'); if (c) c.textContent = fmt(x); }
  const pt = $('#ptime'); if (pt) pt.textContent = fmtP(x);
  const dd = $('#dDur'); if (dd) dd.textContent = fmt(d);
  const mt = $('#miniTime'); if (mt) mt.textContent = `${fmt(x)} / ${fmt(d)}`;
  paintPP(); $$('.sk').forEach(drawMarks);
  $$('[data-act=mstart]').forEach(ms => { ms.classList.toggle('live', S.pending != null); $('span', ms).textContent = S.pending != null ? '+' + fmt(Math.max(0, x - S.pending)) : t('start_btn'); });
  if ('mediaSession' in navigator && PL.el && d) { try { navigator.mediaSession.setPositionState({ duration: d, position: Math.min(x, d), playbackRate: PL.rateV }); } catch (e) {} }
  followTranscript(x);
}, 250);
function playerToolsHTML() {
  const it = PL.item; if (!it || !S.item || it.id !== S.item.id) return '';
  const vid = PL.isVideoFile(it), fine = store.get('fineOpen', false);
  return `<div class="ptools"><button class="chip" data-act="rate-next" aria-label="${t('speed')}"><bdi>${PL.rateV}×</bdi></button>
    <button class="chip" data-act="skip-next" aria-label="${t('skip_by')}"><span class="noico icw">${IC.fwd.replace('<svg', '<svg class="ic"')}</span> <bdi>${skipS()}${LANG === 'ar' ? 'ث' : 's'}</bdi></button>
    <button class="chip ${fine ? 'on' : ''}" data-act="fine-toggle">±0.1</button>
    ${vid ? `<button class="chip" data-act="audio-only" aria-label="${t('audio_only')}">${PL.audioOnly ? '🎬' : '🎧'}</button>` : ''}
    ${vid && !PL.audioOnly ? `<button class="chip" data-act="fs" aria-label="${t('fullscreen')}">⛶</button>` : ''}</div>
    ${fine ? `<div class="fine" dir="ltr"><button class="chip" data-act="fine" data-d="-1">−1</button><button class="chip" data-act="fine" data-d="-0.1">−0.1</button>
      <span class="chip ptime" id="ptime">${fmtP(PL.time())}</span><button class="chip" data-act="fine" data-d="0.1">+0.1</button><button class="chip" data-act="fine" data-d="1">+1</button></div>` : ''}`;
}

/* ================= library ================= */
const itemIcon = i => i.kind === 'youtube' ? '▶️' : i.media === 'video' ? '🎬' : '🎧';
function itemRow(i) {
  const th = i.thumb ? `style="background-image:url('${esc(i.thumb)}')"` : '';
  const dl = i.dl_progress != null;
  return `<a class="li" href="#/item/${i.id}"><div class="th" ${th}>${i.thumb ? '' : itemIcon(i)}${PL.item && PL.item.id === i.id && PL.playing() ? '<span class="now">🔊</span>' : ''}</div>
    <div class="tt"><b dir="auto">${esc(nice(i.title))}</b>
    <small>${i.duration ? `<span>⏱ <bdi>${fmt(i.duration)}</bdi></span>` : ''}${i.bookmarks ? `<span>✂️ ${i.bookmarks}</span>` : ''}
    ${i.trs ? `<span class="okc">📝 ${t('has_tr')}</span>` : ''}${i.excerpts ? `<span>📌 ${i.excerpts}</span>` : ''}${i.notes ? `<span>💡 ${i.notes}</span>` : ''}
    ${!i.dir ? `<span><span class="spin"></span> ${t('reading')}</span>` : dl ? `<span class="dlc">⬇ ${Math.round(i.dl_progress * 100)}٪</span>` : (!i.file && i.url ? `<span class="warnc">🔗 ${t('not_downloaded')}</span>` : '')}</small>
    ${dl ? `<div class="bar thin"><i style="width:${Math.round(i.dl_progress * 100)}%"></i></div>` : ''}</div></a>`;
}
function folderCard(id, name, icon, color, n) {
  if (store.get('libView', 'grid') === 'list') return `<a class="li frow2" href="#/lib/f/${id}" style="--fc:${esc(color || 'var(--acc)')}"><div class="th fi">${esc(icon)}</div><div class="tt"><b dir="auto">${esc(name)}</b><small>${t('items_n', n)}</small></div><span class="chev">‹</span></a>`;
  return `<a class="fcard" href="#/lib/f/${id}" style="--fc:${esc(color || 'var(--acc)')}"><div class="fi">${esc(icon)}</div><b dir="auto">${esc(name)}</b><small>${t('items_n', n)}</small></a>`;
}
const fabHTML = () => `<button class="fab" data-act="add"><b>＋</b> ${t('add')}</button>`;
function placeReminder() {
  const box = $('#rmd'); if (!box) return;
  const h = reminderHTML();
  if (box.dataset.i !== String(store.get('rmi', -1)) || !box.innerHTML || !h) { box.dataset.i = String(store.get('rmi', -1)); box.innerHTML = h; }
  box.hidden = !h;
}
function reminderHTML() {
  const R = window.REMINDERS || []; if (!R.length || S.set.reminders === false) return '';
  let i = store.get('rmi', Math.floor(Math.random() * R.length));
  if (Date.now() - store.get('rmt', 0) > 10 * 60000) { i = (i + 1) % R.length; store.set('rmi', i); store.set('rmt', Date.now()); }
  const x = R[i % R.length];
  return `<button class="rmd ${x.k}" data-act="rmd-next" aria-label="${t('rmd_next')}"><span class="rt">${x.k === 'q' ? `﴿${esc(x.t)}﴾` : `«${esc(x.t)}»`}</span><small>${esc(x.r)}</small></button>`;
}
function heroCard() {
  const pinned = S.items.filter(i => i.pinned).sort((a, b) => b.pinned - a.pinned)[0];
  const it = pinned || S.items.find(i => i.id === store.get('last', null)) || S.items[0];
  if (!it) return '';
  const pos = store.get('pos.' + it.id, 0), d = it.duration || 0, left = d && pos ? Math.max(0, d - pos) : 0;
  const folder = S.folders.find(f => f.id === it.folder_id);
  return `<a class="hero" href="#/item/${it.id}">
    <div class="k"><span>${ICON(pinned ? 'pin' : 'headphones')} ${t(pinned ? 'working_on' : 'continue')}</span><span>${left ? t('left', fmt(left)) : d ? fmt(d) : ''}</span></div>
    <div class="r"><div><b dir="auto">${esc(nice(it.title))}</b><small>${folder ? `<span dir="auto">${esc(folder.name)}</span> · ` : ''}${d ? fmt(d) : ''}</small></div>
      <button class="go" data-act="play-at" data-item="${it.id}" data-t="${pos || 0}" aria-label="${t('play')}">${ICON('play')}</button></div>
    ${d ? `<div class="pb"><i style="width:${Math.min(100, Math.round(pos / d * 100))}%"></i></div>` : ''}</a>`;
}
/* the lessons of the old (Termux) version: offer to bring them over while it is still running */
async function oldBox() {
  const box = $('#oldBox'); if (!box || IS_LAN || IS_WEB) return;
  if (S.impDone) { box.innerHTML = `<div class="banner">✅ <b class="grow minw">${t('imp_done', S.impDone)}</b></div>`; S.impDone = 0; return; }
  if (S.set.imported_old) return;                  // already brought over: nothing to ask the old version
  let st; try { st = await api('/api/import-old'); } catch (e) { return; }
  if (st.state.running) { box.innerHTML = `<div class="banner"><div class="grow minw"><b>${t('imp_busy', st.state.done, st.state.total)}</b><div class="bar"><i style="width:${st.state.total ? Math.round(st.state.done / st.state.total * 100) : 0}%"></i></div></div></div>`; setTimeout(oldBox, 1500); return; }
  if (st.state.error) { box.innerHTML = `<div class="banner warn">⚠️ <span class="grow minw">${esc(st.state.error)}</span><button class="btn warn" data-act="import-old">${t('retry')}</button></div>`; return; }
  if (st.imported) { S.set.imported_old = true; if (st.just_done) { S.impDone = st.just_done; if (/^#\/lib$/.test(location.hash)) vLibrary(); } else box.innerHTML = ''; return; }
  if (!st.old) { box.innerHTML = ''; return; }
  const shared = /\/storage\/emulated\/0\/Maqati$/.test(st.library);
  box.innerHTML = `<div class="banner gold"><div class="grow minw"><b>📦 ${t('imp_found', st.old.items ?? '?', st.old.version || '3')}</b><small>${t(shared ? 'imp_p' : 'imp_noshare')}</small></div>
    <button class="btn pri" data-act="import-old">${t('imp_go')}</button></div>`;
}
async function vLibrary() {
  await loadLib();
  const n = f => S.items.filter(i => f === 'all' ? true : f === 'none' ? !i.folder_id : i.folder_id === f).length;
  view().innerHTML = `<div id="oldBox"></div>
    <div class="h"><h2>${t('library')}</h2><div class="grow"></div>
      <div class="segc viewsw"><button type="button" data-act="lib-view" data-v="grid" class="${store.get('libView', 'grid') === 'grid' ? 'on' : ''}" aria-label="grid">▦</button><button type="button" data-act="lib-view" data-v="list" class="${store.get('libView', 'grid') === 'list' ? 'on' : ''}" aria-label="list">☰</button></div>
      </div>
    ${S.items.filter(i => i.pinned).length > 1 ? `<div class="sectitle">📍 ${t('working_on')}</div><div class="list pinlist">${S.items.filter(i => i.pinned).sort((a, b) => b.pinned - a.pinned).slice(1).map(itemRow).join('')}</div>` : ''}
    <div class="folders ${store.get('libView', 'grid') === 'list' ? 'aslist' : ''}">
      ${folderCard('all', t('all_items'), '🗂️', '#4A5A66', n('all'))}
      <a class="${store.get('libView', 'grid') === 'list' ? 'li frow2' : 'fcard'} works" href="#/works" style="--fc:var(--gold)"><div class="${store.get('libView', 'grid') === 'list' ? 'th fi' : 'fi'}">📦</div><b>${t('my_works')}</b><small>${t('my_works_s')}</small></a>
      ${folderCard('none', t('unsorted'), '📄', '#8a7a5c', n('none'))}
      ${S.folders.map(f => folderCard(f.id, f.name, f.icon || '📁', f.color, n(f.id))).join('')}
      ${store.get('libView', 'grid') === 'list' ? `<button class="li frow2 new" data-act="new-folder"><div class="th fi">＋</div><div class="tt"><b>${t('new_folder')}</b></div></button>` : `<button class="fcard new" data-act="new-folder"><div class="fi">＋</div><b>${t('new_folder')}</b></button>`}
    </div>
    ${S.items.length ? `<div class="sectitle">${t('recent')}</div><div class="list">${S.items.slice(0, 12).map(itemRow).join('')}</div>`
      : `<div class="empty"><div class="big">📚</div><h3>${t('empty_lib')}</h3><p>${t('empty_lib_p')}</p><button class="btn pri big" data-act="add">＋ ${t('add')}</button></div>`}
    ${fabHTML()}`;
  oldBox();
}
function workRow(w) {
  const when = w.start != null && w.end ? `<button class="chip when" data-act="play-at" data-item="${w.item_id}" data-t="${w.start}">▶ ${rng(w.start, w.end)}</button>` : '';
  return w.type === 'tr'
    ? fileRow({ path: w.path || '', name: w.name, sub: esc(nice(w.item_title || '')), icon: IC.doc, noOpen: true, when, locked: w.locked,
        tap: `data-act="open-tr" data-item="${w.item_id}" data-k="${w.id}"`,
        btns: `<button class="ibtn" data-act="open-tr" data-item="${w.item_id}" data-k="${w.id}" aria-label="open">${IC.doc}</button><button class="ibtn" data-act="export-tr" data-tid="${w.id}" data-title="${esc(w.name)}" aria-label="export">📕</button>` })
    : fileRow({ path: w.path, name: w.name, size: w.size, clip: true, sub: esc(nice(w.item_title || '')), when, locked: w.locked });
}
/* ================= home: what you are on, what is running, your latest works ================= */
async function vHome() {
  await loadLib();
  const c = S.items.length ? await api('/api/folders/all/contents').catch(() => null) : null;
  const works = (c && c.works || []).slice(0, 5);
  const n = f => S.items.filter(i => f === 'all' ? true : f === 'none' ? !i.folder_id : i.folder_id === f).length;
  view().innerHTML = `<div class="home">
    <div class="hmain">
      <form class="hsearch" id="hs" role="search"><input id="hq" dir="auto" placeholder="${t('home_search_ph')}" enterkeyhint="search" autocomplete="off" aria-label="${t('search')}"><button class="btn pri" aria-label="${t('search')}">${ICON('search')}</button></form>
      ${heroCard() || `<button class="hero first" data-act="add"><div class="r"><div><b>${t('first_lesson')}</b><small>${t('first_lesson_p')}</small></div><span class="go">${ICON('plus')}</span></div></button>`}
      <div class="sectitle">${ICON('clock')} ${t('now_running')}<a class="more" href="#/tasks">${t('tasks')}</a></div><div id="homeJobs"></div>
      <div class="sectitle">${ICON('box')} ${t('recent_works')}<a class="more" href="#/works">${t('see_all')}</a></div>
      ${works.length ? `<div class="card pad">${works.map(workRow).join('')}</div>` : `<p class="muted small hint">${t('works_empty')}</p>`}
    </div>
    <aside class="hside">
      <div class="sectitle">${ICON('folders')} ${t('your_folders')}<a class="more" href="#/lib">${t('library')}</a></div>
      <div class="folders">${folderCard('all', t('all_items'), '🗂️', '#4A5A66', n('all'))}${S.folders.slice(0, 7).map(f => folderCard(f.id, f.name, f.icon || '📁', f.color, n(f.id))).join('')}</div>
    </aside></div>${fabHTML()}`;
  renderHomeJobs();
  $('#hs').onsubmit = e => { e.preventDefault(); S.q = $('#hq').value.trim(); location.hash = '#/search'; };
}
function renderHomeJobs() {
  const box = $('#homeJobs'); if (!box) return;
  const now = S.jobs.filter(j => j.status !== 'done' && j.status !== 'cancelled').slice(0, 4);
  const sig = now.map(j => j.id + j.status + Math.round((j.progress || 0) * 100) + (j.message || '')).join('|');
  if (box.dataset.sig === sig) return;
  box.dataset.sig = sig;
  box.innerHTML = now.length ? `<div class="hjobs">${now.map(j => `<a class="hjob ${j.status}" href="#/tasks"><div class="jt"><b dir="auto" class="ell">${esc(nice(j.title))}</b><span class="st ${j.status}">${t('st_' + j.status)}</span></div>
    ${j.status === 'running' || j.status === 'paused' ? `<div class="bar thin"><i style="width:${Math.round((j.progress || 0) * 100)}%"></i></div>` : ''}
    <small class="muted ell" dir="auto">${esc(j.message || '')}${j.eta ? ' · ' + leftTxt(j) : ''}</small></a>`).join('')}</div>` : `<p class="muted small hint">${t('nothing_running')}</p>`;
}
async function vFolder(fid, tab, mine) {
  tab = tab || 'lessons';
  await loadLib();
  const f = S.folders.find(x => String(x.id) === fid);
  const name = mine ? t('my_works') : fid === 'all' ? t('all_items') : fid === 'none' ? t('unsorted') : f ? f.name : '?';
  const icon = mine ? '📦' : fid === 'all' ? '🗂️' : fid === 'none' ? '📄' : (f && f.icon) || '📁';
  const tabs = [['lessons', '🎧', 'tab_lessons'], ['works', '📦', 'tab_works'], ['parts', '✂️', 'tab_parts'], ['ex', '📌', 'tab_ex']];
  view().innerHTML = `
    <div class="crumbs"><a href="#/lib">${t('library')}</a> ${SEP()}</div>
    <div class="h"><h2>${esc(icon)} <span dir="auto">${esc(name)}</span></h2><div class="grow"></div>
      ${mine ? '' : `<button class="ib more" data-act="folder-menu" data-id="${fid}" aria-label="${t('more_opts')}">${ICON('dots')}</button>`}</div>
    ${mine ? `<p class="muted small" style="margin:-8px 2px 12px">${t('works_all_p')}</p>` : `<div class="ftabs">${tabs.map(([k, i, n]) => `<a href="#/lib/f/${fid}/${k}" class="${tab === k ? 'on' : ''}">${i} ${t(n)}</a>`).join('')}</div>`}
    <div id="fbody"></div>${fabHTML()}`;
  if (tab === 'lessons') {
    let list = S.items.filter(i => fid === 'all' ? true : fid === 'none' ? !i.folder_id : String(i.folder_id) === fid);
    const sort = store.get('sort', 'new'), filter = (S.ffilter || '').trim().toLowerCase();
    if (filter) list = list.filter(i => (i.title || '').toLowerCase().includes(filter));
    if (sort === 'name') list = [...list].sort((a, b) => nice(a.title).localeCompare(nice(b.title), LANG));
    $('#fbody').innerHTML = `<div class="toolbar"><input class="input" style="flex:1;min-width:140px" id="ffilter" placeholder="${t('filter')}" value="${esc(S.ffilter || '')}">
      ${segc('sort', sort, [['new', t('newest')], ['name', t('by_name')]], 'data-sort')}</div>
      <div class="list">${list.map(itemRow).join('') || `<div class="empty"><div class="big">🗂️</div><p>${t('empty_folder')}</p></div>`}</div>`;
    $('#ffilter').oninput = e => { S.ffilter = e.target.value; clearTimeout(vFolder.t); vFolder.t = setTimeout(() => vFolder(fid, tab).then(() => { const i = $('#ffilter'); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }), 300); };
    $$('[data-sort] button').forEach(b => b.onclick = () => { store.set('sort', b.dataset.v); vFolder(fid, tab); });
    return;
  }
  const c = await api(`/api/folders/${fid}/contents`);
  S.fc = c;
  if (tab === 'works') {
    const ff = mine ? (S.wfold || 'all') : 'all', inF = w => { const it = S.items.find(i => i.id === w.item_id); return ff === 'all' || String(it ? it.folder_id || 'none' : 'none') === String(ff); };
    const ft = S.wf || 'all', ws = c.works.filter(w => (ft === 'all' || w.type === ft) && inF(w));
    const n = k => c.works.filter(w => (k === 'all' || w.type === k) && inF(w)).length;
    $('#fbody').innerHTML = `${mine ? '' : `<p class="muted small">${t('works_p')}</p>`}
      ${mine && S.folders.length ? `<div class="chips scroll" style="margin-bottom:10px">${[['all', t('all_items')], ...S.folders.map(f => [f.id, f.name]), ['none', t('unsorted')]].map(([k, l]) =>
        `<button class="chip ${String(ff) === String(k) ? 'on' : ''}" data-act="wfold" data-k="${k}"><span dir="auto">${esc(l)}</span></button>`).join('')}</div>` : ''}
      <div class="toolbar">${segc('wf', ft, [['all', `${t('w_all')} ${n('all')}`], ['tr', `📝 ${t('w_tr')} ${n('tr')}`], ['audio', `🎵 ${t('w_audio')} ${n('audio')}`], ['video', `🎬 ${t('w_video')} ${n('video')}`]], 'data-wf')}</div>
      ${ws.length ? `<div class="card pad">${ws.map(workRow).join('')}</div>`
        : `<div class="empty"><div class="big">📦</div><p>${t('works_empty')}</p></div>`}`;
    $$('[data-wf] button').forEach(b => b.onclick = () => { S.wf = b.dataset.v; vFolder(fid, tab, mine); });
    return;
  }
  if (tab === 'parts') {
    $('#fbody').innerHTML = c.marks.length ? `<div class="list">${c.marks.map(m => `
      <div class="card pad frow" data-item="${m.item_id}"><div class="frow-h"><button class="play" data-act="play-at" data-item="${m.item_id}" data-t="${m.start}">▶</button>
        <div class="grow minw"><b dir="auto">${esc(m.name || t('untitled'))}</b><small dir="auto" class="muted ell">${esc(nice(m.item_title))} · ${m.end != null ? rng(m.start, m.end) : `<bdi>${fmt(m.start)}</bdi>`}</small></div></div>
        <div class="btns">${clipBtns(c.jobs, j => j.bookmark_id === m.id, `data-b="${m.id}"`, m.media === 'video' || m.kind === 'youtube')}</div></div>`).join('')}</div>`
      : `<div class="empty"><div class="big">✂️</div><p>${t('parts_empty')}</p></div>`;
  } else {
    $('#fbody').innerHTML = c.excerpts.length ? `<div class="toolbar"><button class="btn gold" data-act="export-folder-ex" data-id="${fid}">📕 ${t('dl_book_all')}</button></div>
      <div class="list">${c.excerpts.map(x => exCard(x, c.jobs, true)).join('')}</div>`
      : `<div class="empty"><div class="big">📌</div><p>${t('ex_empty_f')}</p></div>`;
  }
}
/* the quality list that drops down under a download button: the original first, then smaller */
function closeQ() { $$('.qmenu').forEach(x => x.remove()); }
document.addEventListener('pointerdown', e => { if (!e.target.closest('.qmenu, [data-act=qmenu]')) closeQ(); }, true);
window.addEventListener('scroll', closeQ, { passive: true });
function placeQ(box, el) {
  const r = el.getBoundingClientRect(), w = Math.min(250, innerWidth - 24);
  box.style.width = w + 'px';
  box.style.left = Math.max(12, Math.min(r.left + r.width / 2 - w / 2, innerWidth - w - 12)) + 'px';
  const below = r.bottom + 6, h = box.offsetHeight;
  box.style.top = (below + h > innerHeight - 70 ? Math.max(12, r.top - 6 - h) : below) + 'px';
}
async function qMenu(el, itemId, fmtk, pick) {
  const was = el.classList.contains('qopen'); closeQ(); $$('.qopen').forEach(x => x.classList.remove('qopen')); if (was) return;
  el.classList.add('qopen');
  const box = document.createElement('div'); box.className = 'qmenu';
  box.innerHTML = `<div class="qh">${t('quality')}</div><div class="qwait"><span class="spin"></span> ${t('q_reading')}</div>`;
  (document.querySelector('dialog[open]') || document.body).appendChild(box); placeQ(box, el);
  S.qc = S.qc || {};
  let q = S.qc[itemId];
  if (!q) { q = await Promise.race([api(`/api/items/${itemId}/qualities?probe=1`).catch(() => null), new Promise(r => setTimeout(() => r(null), 8000))]); if (q) S.qc[itemId] = q; }   // never wait long: the standard list is better than no list
  if (!box.isConnected) return;
  q = q || { video: [1080, 720, 480, 360, 240, 144], audio: [0, 192, 128, 96, 64], top: 0 };
  const tag = h => h >= 1080 ? ' · Full HD' : h >= 720 ? ' · HD' : h <= 240 ? ` · ${t('q_small')}` : '';
  const opts = fmtk === 'mp3'
    ? q.audio.map(k => [k, k ? `${k} kbps${k <= 64 ? ' · ' + t('q_small') : ''}` : `⭐ ${t('q_orig')} · ${t('q_best_a')}`])
    : [[9999, `⭐ ${t('q_orig')}${q.top ? ` · ${q.top}p` : ''}`], ...q.video.filter(h => h !== q.top).map(h => [h, `${h}p${tag(h)}`])];
  box.innerHTML = `<div class="qh">${fmtk === 'mp3' ? '🎵 MP3' : '🎬 ' + t('video')} · ${t('quality')}</div>` +
    opts.map(([v, l], i) => `<button type="button" data-q="${v}" class="${i === 0 ? 'top' : ''}" dir="auto">${l}</button>`).join('');
  box.onclick = e => { const b = e.target.closest('[data-q]'); if (!b) return; closeQ(); el.classList.remove('qopen'); pick(+b.dataset.q); };
  placeQ(box, el);
}
const qdd = (f, attrs = '', mode = '') => `<button class="btn qdd" data-act="qmenu" data-f="${f}" ${attrs} ${mode ? `data-mode="${mode}"` : ''} aria-label="quality">▾</button>`;
/* status-aware buttons for a cut part: shows progress, then ▶ / ⬇ when the file is ready */
function clipBtns(jobs, match, attrs, vid, only) {
  const one = fmtk => {
    const j = [...jobs].reverse().find(x => x.kind === 'clip' && (x.params.fmt || 'mp3') === fmtk && match(x));
    const label = fmtk === 'mp3' ? 'MP3' : t('video');
    if (!j) return `<span class="split"><button class="btn" data-act="clip" data-f="${fmtk}" ${attrs}>⬇ ${label}</button>${qdd(fmtk, attrs)}</span>`;
    if (j.status === 'done' && j.result) return `<span class="ready split"><button class="btn ok" data-act="play-file" data-path="${esc(j.result)}">▶ ${label}${j.taken ? ` <small class="tk">✓ ${dur(j.taken)}</small>` : ''}</button><a class="btn ok" href="${mediaURL(j.result)}?dl=1">⬇</a>${qdd(fmtk, attrs)}</span>`;
    if (j.status === 'error') return `<button class="btn warn" data-act="job-retry" data-j="${j.id}">⚠️ ${label} · ${t('retry_short')}</button>`;
    return `<button class="btn busy" disabled>⏳ ${label} <bdi>${Math.round((j.progress || 0) * 100)}%</bdi>${j.eta ? ` <small class="tk">~${dur(j.eta)}</small>` : ''}</button>`;
  };
  return only === 'video' ? one('video') : only === 'mp3' ? one('mp3') : one('mp3') + (vid ? one('video') : '');
}
function exCard(x, jobs, showItem) {
  const open = S.exOpen === x.id;
  return `<div class="card pad excard" data-x="${x.id}" data-item="${x.item_id}">
    <div class="frow-h"><button class="play" data-act="play-at" data-item="${x.item_id}" data-t="${x.start}">▶</button>
      <div class="grow minw"><b dir="auto" class="extitle" data-act="ex-rename">📌 ${esc(x.title || t('untitled'))}</b>
      <small class="muted ell" dir="auto">${showItem ? esc(nice(x.item_title)) + ' · ' : ''}${rng(x.start, x.end)}</small></div></div>
    <p class="extext ${open ? 'open' : ''}" dir="auto">${esc(x.text || '')}</p>
    ${(x.text || '').length > 160 ? `<button class="lnk" data-act="ex-more">${open ? t('less') : t('more')}</button>` : ''}
    <div class="btns">${clipBtns(jobs || [], j => j.params && j.params.excerpt_id === x.id, `data-ex="${x.id}"`, false)}
      <button class="btn gold" data-act="export-ex">📕 ${t('download')}</button><button class="btn" data-act="ex-proj">${PJADD} ${t('to_project')}</button>
      <button class="btn ghost" data-act="ex-copy">📋</button><button class="btn ghost danger" data-act="ex-del">🗑</button></div></div>`;
}

const COLORS = ['#0F5C4D', '#1F4E79', '#4A5A66', '#8A6A2B'];   // four calm colours
const OLD_COLORS = { '#0d6e5f': '#0F5C4D', '#1e3a5f': '#1F4E79', '#5b6b73': '#4A5A66', '#8a6d3b': '#8A6A2B' };
const GONE = ['#8250df', '#bf3989'];
const ICONS = ['📁', '📚', '🕌', '📖', '🎓', '🧠', '💡', '❤️', '⭐', '🌙', '☀️', '🌿', '🎧', '🎬', '📝', '🗂️', '💼', '🔖', '🏷️', '👨‍🏫', '🤲', '📿', '🕋', '✨'];
async function customizeFolder(f) {
  let color = f ? f.color || COLORS[0] : COLORS[0], icon = f ? f.icon || '📁' : '📁';
  const r = await sheet(f ? t('customize') : t('new_folder'), `
    <div class="field"><label>${t('folder_name')}</label><input id="fn" dir="auto" value="${esc(f ? f.name : '')}"></div>
    <div class="field"><label>${t('icon')}</label><div class="icons">${ICONS.map(i => `<button type="button" data-i="${i}" class="${i === icon ? 'on' : ''}">${i}</button>`).join('')}</div></div>
    <div class="field"><label>${t('color')}</label><div class="swatches">${COLORS.map(c => `<button type="button" data-c="${c}" style="background:${c}" class="${c === color ? 'on' : ''}"></button>`).join('')}</div></div>`,
    `<button class="btn big" value="no">${t('cancel')}</button><button class="btn big pri" value="ok">${t('save')}</button>`, d => {
      $$('[data-i]', d).forEach(b => b.onclick = e => { e.stopPropagation(); icon = b.dataset.i; $$('[data-i]', d).forEach(x => x.classList.toggle('on', x === b)); });
      $$('[data-c]', d).forEach(b => b.onclick = e => { e.stopPropagation(); color = b.dataset.c; $$('[data-c]', d).forEach(x => x.classList.toggle('on', x === b)); });
      if (!f) setTimeout(() => $('#fn', d).focus(), 60);
    });
  if (r !== 'ok') return null;
  const name = $('#fn').value.trim() || t('new_folder');
  if (f) { await patch('/api/folders/' + f.id, { name, icon, color }); return f.id; }
  const n = await post('/api/folders', { name }); await patch('/api/folders/' + n.id, { icon, color }); return n.id;
}

/* ---------- add ---------- */
async function addSheet() {
  await loadLib();
  const cur = (location.hash.match(/^#\/lib\/f\/(\d+)/) || [])[1] || (S.item && S.item.folder_id) || '';
  let mode = store.get('addmode', 'links'), files = [], how = S.set.auto_download || 'video';
  const folderOpts = `<option value="">${t('unsorted')}</option>` + S.folders.map(f => `<option value="${f.id}" ${String(cur) === String(f.id) ? 'selected' : ''}>${esc((f.icon || '📁') + ' ' + f.name)}</option>`).join('');
  await sheet('＋ ' + t('add'), `
    <div class="segc big" style="margin-bottom:14px"><button data-m="links">🔗 ${t('links')}</button><button data-m="files">📁 ${t('files')}</button></div>
    <div data-p="links"><div class="field"><textarea id="linksIn" dir="ltr" placeholder="${t('links_ph')}" style="min-height:110px"></textarea><small>${t(IS_WEB ? 'links_hint_web' : 'links_hint')}</small></div>
      <div class="field"><label>${t('add_how')}</label>${segc('how', how, [['video', t('as_video')], ['audio', t('as_audio')], ['none', t('as_link')]])}<small>${t('add_how_p')}</small></div>
      <div class="field" id="addQF"><label>🎬 ${t('quality')}</label><select id="addQ"><option value="">${t('q_default', S.set.video_height >= 9999 ? t('q_orig') : (S.set.video_height || 720) + 'p')}</option>
        <option value="9999">⭐ ${t('q_orig')}</option>${[1080, 720, 480, 360, 240, 144].map(h => `<option value="${h}">${h}p</option>`).join('')}</select></div></div>
    <div data-p="files"><div class="field"><button class="btn soft big wide" id="pick">📁 ${t('choose_files')}</button><input type="file" id="fileIn" multiple accept="audio/*,video/*" hidden>
      <small id="fl" style="text-align:center">${t('drop')}</small><div id="upProg" class="muted" style="margin-top:8px"></div></div></div>
    <div class="field"><label>${t('into_folder')}</label><select id="addFolder">${folderOpts}</select></div>`,
    `<button class="btn pri big wide" id="addGo">＋ ${t('add')}</button>`, (d, close) => {
      const setMode = m => { mode = m; store.set('addmode', m); $$('[data-m]', d).forEach(b => b.classList.toggle('on', b.dataset.m === m)); $$('[data-p]', d).forEach(p => p.hidden = p.dataset.p !== m); };
      $$('[data-m]', d).forEach(b => b.onclick = () => setMode(b.dataset.m)); setMode(mode);
      wireSegc(d, (k, v) => { if (k === 'how') { how = v; $('#addQF', d).hidden = v !== 'video'; } }); $('#addQF', d).hidden = how !== 'video';
      const fin = $('#fileIn', d), setFiles = fl => { files = [...fl]; $('#fl', d).textContent = files.map(f => f.name).join('، '); };
      $('#pick', d).onclick = () => fin.click(); fin.onchange = () => setFiles(fin.files);
      d.ondragover = e => e.preventDefault(); d.ondrop = e => { e.preventDefault(); setMode('files'); setFiles(e.dataTransfer.files); };
      $('#addGo', d).onclick = async () => {
        const fid = $('#addFolder', d).value || null;
        try {
          if (mode === 'links') {
            const txt = $('#linksIn', d).value; if (!/https?:\/\//.test(txt)) return toast(t('no_links'));
            const r = await post('/api/links', { text: txt, folder_id: fid ? +fid : null, mode: how, q: +$('#addQ', d).value || null });
            close('ok'); toast(t('added')); pollJobs(); location.hash = '#/item/' + r.ids[0];
          } else {
            if (!files.length) return toast(t('choose_first'));
            if (IS_WEB) { const lim = /iPhone|iPad/.test(navigator.userAgent) ? 300e6 : 1500e6; const big = files.find(f => f.size > lim); if (big) return toast(t('too_big_web', big.name, size(big.size), size(lim)), null, 9000); }
            $('#addGo', d).disabled = true;
            const ids = await upload(files, fid, p => $('#upProg', d).textContent = t('uploading', Math.round(p * 100)));
            close('ok'); toast(t('added')); location.hash = '#/item/' + ids[0];
          }
        } catch (e) { toast(e.message); $('#addGo', d).disabled = false; }
      };
    });
}
async function upload(files, fid, onp) {
  const total = files.reduce((a, f) => a + f.size, 0) || 1; let sent = 0; const ids = [];
  for (const f of files) {
    const r = await new Promise((res, rej) => {
      const x = new XMLHttpRequest();
      x.open('POST', `/api/upload?name=${encodeURIComponent(f.name)}${fid ? '&folder_id=' + fid : ''}`);
      x.upload.onprogress = e => onp((sent + e.loaded) / total);
      x.onload = () => x.status < 300 ? res(JSON.parse(x.responseText)) : rej(new Error('Upload failed'));
      x.onerror = () => rej(new Error('Upload failed')); x.send(f);
    });
    sent += f.size; ids.push(...r.ids);
  }
  return ids;
}

/* ================= lesson page ================= */
function leaveItemPage() { S.item = null; S.editTr = false; S.pick = null; if (PL.kind === 'yt') PL.unload(); ui(); }
async function vItem(id, at) {
  const d = await api('/api/items/' + id).catch(() => null);
  if (!new RegExp('^#/item/' + id + '(/|$)').test(location.hash)) return;     // the user already went elsewhere
  if (!d) { location.hash = '#/lib'; return; }
  if (!S.item || S.item.id !== id) { S.sel.clear(); S.tr = { key: store.get('tr.' + id, 'all'), segs: [] }; S.editTr = false; }
  S.item = d; await loadLib();
  PL.load(d, at, at != null);
  view().innerHTML = `
    <div class="crumbs">${crumbFolder(d)}</div>
    <div class="itemgrid"><div class="col-play">
      <div class="itemhead"><div class="titlebox"><h2 class="t" dir="auto" data-act="rename-item" id="itTitle">${esc(nice(d.title))}</h2>
        <div class="meta" id="itMeta"></div></div><button class="ib more" data-act="item-menu" aria-label="${t('more_opts')}">${ICON('dots')}</button></div>
      <div id="banner"></div>
      <div class="player" id="player"></div>
      <div id="pl-tools"></div>
    </div><div class="col-secs" id="secs"></div></div>`;
  renderMeta(); renderBanner(); renderSections(); PL.place();
}
function crumbFolder(d) { const f = S.folders.find(x => x.id === d.folder_id); return `<a href="#/lib">${t('library')}</a> ${SEP()} <a href="#/lib/f/${f ? f.id : 'none'}">${esc(f ? f.name : t('unsorted'))}</a> ${SEP()}`; }
function renderMeta() {
  const d = S.item, f = S.folders.find(x => x.id === d.folder_id);
  $('#itMeta').innerHTML = `<button class="chip acc" data-act="move-item">${esc((f && f.icon) || '📁')} <span dir="auto">${esc(f ? f.name : t('unsorted'))}</span></button>
    ${d.duration ? `<span class="mtx"><bdi>${fmt(d.duration)}</bdi></span>` : ''}
    ${d.pinned ? `<span class="mtx gold">📍 ${t('pinned')}</span>` : ''}${d.projects.length ? `<span class="mtx">💼 ${d.projects.length}</span>` : ''}`;
}
function renderBanner() {
  const d = S.item, b = $('#banner'); if (!b) return;
  const act = [...d.jobs].reverse().find(j => !j.bookmark_id && ['fetch', 'info'].includes(j.kind) && ['running', 'queued', 'paused', 'error'].includes(j.status));
  const tr = [...d.jobs].reverse().find(j => !j.bookmark_id && j.kind === 'transcribe' && ['running', 'queued'].includes(j.status));
  let h = '';
  if (act) {
    const pct = Math.round((act.progress || 0) * 100), what = act.params.want === 'video' ? t('the_video') : t('the_audio');
    h += act.status === 'error' ? `<div class="banner warn">⚠️ <span class="grow minw" dir="auto">${esc(act.message)}</span><button class="btn warn" data-act="job-retry" data-j="${act.id}">${t('retry')}</button></div>`
      : `<div class="banner"><div class="grow minw"><b>⬇ ${act.kind === 'info' ? t('reading_link') : t('dl_banner', what)} <bdi>${pct}%</bdi></b><small>${t('dl_banner_p')}</small>
          <div class="bar"><i style="width:${pct}%"></i></div>${act.eta ? `<small class="eta">⏱ ${leftTxt(act)}</small>` : ''}</div></div>`;
  }
  if (tr && false) { const pct = Math.round((tr.progress || 0) * 100); h += `<div class="banner"><div class="grow minw"><b>📝 ${t('busy_tr')} <bdi>${pct}%</bdi></b><small dir="auto">${esc(tr.message || '')}</small><div class="bar"><i style="width:${pct}%"></i></div>${tr.eta ? `<small class="eta">⏱ ${leftTxt(tr)}</small>` : ''}</div></div>`; }
  if (b.innerHTML !== h) b.innerHTML = h;
}
async function refreshItem(opts = {}) {
  if (!S.item) return;
  const want = S.item.id;
  const d = await api('/api/items/' + want).catch(() => null); if (!d || !S.item || S.item.id !== want || d.id !== want) return;
  const srcChanged = d.file !== S.item.file;
  S.item = d;
  if (srcChanged && PL.item && PL.item.id === d.id) { const at = PL.time(), was = PL.playing(); PL.unload(); PL.load(d, at || null, was); if (d.file) toast(t('dl_done')); }
  $('#itTitle').textContent = nice(d.title);
  renderMeta(); renderBanner(); renderSections(opts); PL.place();
}
const TAB_OF = { marks: 'marks', tr: 'tr', ex: 'notes', notes: 'notes', files: 'files' };
function secHTML(key, icon, title, n, body) {
  const on = TAB_OF[key] === store.get('itab', 'marks');
  return `<section class="sec ${on ? 'show' : ''}" data-sec="${key}"><div class="sectop"><span class="ico">${icon}</span><b class="minw">${title}</b>${n ? `<span class="n">${n}</span>` : ''}</div><div class="secbody" id="sb-${key}">${body}</div></section>`;
}
function showTab(k) {
  store.set('itab', k);
  $$('#itabs button').forEach(b => b.classList.toggle('on', b.dataset.k === k));
  $$('#secs .sec').forEach(x => x.classList.toggle('show', TAB_OF[x.dataset.sec] === k));
}
function openFiles() { }   // a new task no longer switches tabs: the person stays where they are
function renderSections(opts = {}) {
  const d = S.item, host = $('#secs'); if (!host) return;
  const active = document.activeElement;
  if (opts.soft && active && host.contains(active) && /INPUT|TEXTAREA/.test(active.tagName)) return;   // don't disturb typing
  const trOld = opts.keepTr && $('#sb-tr') ? $('#sb-tr').innerHTML : null;
  const y = window.scrollY;
  if (opts.soft && $('#itabs')) {                   // live update: same page, only what changed inside each tab
    const parts = { marks: marksHTML(), ex: exListHTML(), notes: notesHTML(), files: filesHTML() };
    for (const [k, html] of Object.entries(parts)) { const el = $('#sb-' + k); if (el && el.innerHTML !== html) el.innerHTML = html; }
    const cnt2 = { marks: d.bookmarks.length, tr: d.transcripts.length, notes: d.notes.length + d.excerpts.length, files: d.files.length };
    $$('#itabs button').forEach(b => { const n = cnt2[b.dataset.k], sm = $('small', b); if (sm) sm.textContent = n || ''; else if (n) b.insertAdjacentHTML('beforeend', `<small>${n}</small>`); });
    if (!opts.keepTr && S.set.show_transcript !== false) loadTranscript();
    return;
  }
  const tab = store.get('itab', 'marks'), cnt = { marks: d.bookmarks.length, tr: d.transcripts.length, notes: d.notes.length + d.excerpts.length, files: d.files.length };
  host.innerHTML = `<div class="itabs" id="itabs" role="tablist">${[['marks', 'sec_marks_s'], ...(S.set.show_transcript !== false ? [['tr', 'sec_tr_s']] : []), ['notes', 'sec_notes_s'], ['files', 'sec_files_s']].map(([k, l]) =>
    `<button role="tab" data-act="itab" data-k="${k}" class="${tab === k ? 'on' : ''}">${t(l)}${cnt[k] ? `<small>${cnt[k]}</small>` : ''}</button>`).join('')}</div>` + [
    secHTML('marks', '✂️', t('sec_marks'), d.bookmarks.length, marksHTML()),
    S.set.show_transcript !== false ? secHTML('tr', '📝', t('sec_tr'), d.transcripts.length, '') : '',
    secHTML('ex', '📌', t('sec_ex'), d.excerpts.length, exListHTML()),
    secHTML('notes', '💡', t('sec_notes'), d.notes.length, notesHTML()),
    secHTML('files', '📁', t('sec_files'), d.files.length, filesHTML()),
  ].join('');
  if (S.set.show_transcript !== false) { if (trOld != null) $('#sb-tr').innerHTML = trOld; else loadTranscript(); }
  window.scrollTo(0, y);
}

/* ---------- parts & bookmarks ---------- */
function marksHTML() {
  const d = S.item, vid = d.media === 'video' || d.kind === 'youtube';
  const typed = `<button class="btn soft wide" data-act="part-typed" style="margin-bottom:8px">✂️ ${t('part_typed')}</button>`;
  if (!d.bookmarks.length) return typed + `<p class="muted">${t('marks_empty')}</p>`;
  for (const id of [...S.sel]) if (!d.bookmarks.some(b => b.id === id)) S.sel.delete(id);
  const n = S.sel.size;
  const trJob = b => [...d.jobs].reverse().find(j => j.kind === 'transcribe' && j.bookmark_id === b.id);
  return `${n ? `<div class="bulk"><b>${t('selected_n', n)}</b><div class="grow"></div>
      <span class="split"><button class="btn pri" data-act="bulk" data-a="mp3">⬇ MP3</button>${qdd('mp3', '', 'bulk')}</span>${vid ? `<span class="split"><button class="btn" data-act="bulk" data-a="video">⬇ ${t('video')}</button>${qdd('video', '', 'bulk')}</span>` : ''}
      <button class="btn" data-act="bulk" data-a="transcribe">📝 ${t('transcribe')}</button><button class="btn" data-act="bulk" data-a="project">${PJADD} ${t('to_project')}</button>
      <button class="btn ghost" data-act="sel-none">✕</button></div>` : ''}
    ${typed}<div class="btns" style="margin-bottom:6px"><button class="chip ${S.selMode ? 'on' : ''}" data-act="sel-mode">☑ ${t('select')}</button>
      ${S.selMode ? `<label class="chip"><input type="checkbox" data-act="sel-all" ${n && n === d.bookmarks.length ? 'checked' : ''}> ${t('select_all')}</label>` : ''}
      <button class="chip gold" data-act="export" data-which="clips">📕 ${t('export_book')}</button></div>
    ${d.bookmarks.map(b => { const tj = trJob(b); return `
    <div class="mark ${b.end == null ? 'pt' : ''} ${b.done ? 'done' : ''}" data-b="${b.id}">
      <div class="r1">${S.selMode ? `<input type="checkbox" class="sel" data-act="sel" ${S.sel.has(b.id) ? 'checked' : ''}>` : ''}
        <div class="mt"><input class="nm" dir="auto" data-edit="mark-name" value="${esc(b.name)}" placeholder="${t('untitled')}" ${b.done ? 'readonly' : ''}>
          <button class="mtime" data-act="seek" data-t="${b.start}">${b.end != null ? rng(b.start, b.end) : `<bdi>${fmt(b.start)}</bdi>`}</button></div>
        ${b.done ? `<span class="chip okc">✓ ${t('done_lock')}</span>` : ''}</div>
      ${S.lockAsk === b.id ? `<div class="btns lockrow"><button class="btn ${b.done ? '' : 'pri'} lockok" data-act="mark-done-ok">${b.done ? '🔓 ' + t('unlock_ok') : '✓ ' + t('lock_ok')}</button><button class="btn ghost" data-act="mark-done-no">✕</button></div>` : ''}
      ${b.end == null && !b.done ? `<button class="btn soft wide" data-act="set-end">🔴 ${t('set_end')}</button>` : ''}
      <div class="mbar"><button class="btn icon" data-act="seek" data-t="${b.start}" aria-label="${t('play')}">▶</button>
        ${clipBtns(d.jobs, j => j.bookmark_id === b.id, '', vid)}
        ${tj && tj.status === 'done' ? `<button class="btn ok" data-act="tr-pick-b" data-b="${b.id}">📝 ✓</button>`
          : tj && ['running', 'queued'].includes(tj.status) ? `<button class="btn busy" disabled>📝 <bdi>${Math.round((tj.progress || 0) * 100)}%</bdi></button>`
          : `<button class="btn" data-act="one" data-a="transcribe">📝 ${t('transcribe')}</button>`}
        <button class="btn icon" data-act="mark-more" aria-label="${t('more_opts')}">${ICON('dots')}</button></div>
      <div class="inl"></div>
      ${b.note || S.noteOpen === b.id ? `<textarea class="note" dir="auto" data-edit="mark-note" placeholder="${t('note_ph')}" ${b.done ? 'readonly' : ''}>${esc(b.note || '')}</textarea>` : ''}
    </div>`; }).join('')}`;
}
async function markTimes(b) {
  const ready = S.item.jobs.filter(j => j.kind === 'clip' && j.bookmark_id === b.id && j.status === 'done' && j.result);
  const r = await sheet(t('edit_times'), `${teHTML('ta', t('start'), b.start, 'start')}${teHTML('tb', t('end_opt'), b.end, 'end', '—')}
    <small class="muted">${t('time_fmt')}</small>
    ${ready.length ? `<label class="sw"><span>${t('recut_files')} (${ready.length})</span><input type="checkbox" id="trecut" checked></label>` : ''}`,
    `<button class="btn big" value="no">${t('cancel')}</button><button class="btn big pri" value="ok">${t('save')}</button>`,
    d => wireTE(d, mainPlayer(S.item.id)));
  if (r !== 'ok') return;
  const a = parseT($('#ta').value), e = parseT($('#tb').value);
  if (a == null || a === undefined || e === undefined || (e != null && e <= a)) return toast(t('bad_time'));
  await patch('/api/bookmarks/' + b.id, e == null ? { start: a, clear_end: true } : { start: a, end: e });
  if (ready.length && $('#trecut') && $('#trecut').checked && e != null) {
    for (const j of ready) await post('/api/clipfile', { path: j.result, action: 'recut', start: a, end: e });
    toast(t('in_tasks')); pollJobs();
  }
  refreshItem({ keepTr: true });
}
const teHTML = (id, label, v, role, ph = '') => `<div class="field te" data-te="${id}" data-role="${role}"><label>${label}</label>
  <div class="terow" dir="ltr"><button type="button" class="btn" data-tn="-1">−1</button><button type="button" class="btn" data-tn="-0.1">−0.1</button>
    <input id="${id}" inputmode="decimal" autocomplete="off" value="${v == null ? '' : fmtP(v)}" placeholder="${esc(ph)}"><button type="button" class="btn" data-tn="0.1">+0.1</button><button type="button" class="btn" data-tn="1">+1</button></div>
  <div class="terow2"><button type="button" class="btn soft" data-tnow>⏱ ${t('from_player')}</button><button type="button" class="btn" data-tplay>▶ ${t('listen')}</button></div></div>`;
/* a player the time editor can read and preview with: the main player, or a media element in a window */
function mainPlayer(itemId) {
  if (!PL.item || PL.item.id !== itemId || !PL.ready()) return null;
  return { now: () => PL.time(), play: (x, stop) => { PL.seek(Math.max(0, x), true); clearInterval(S.pvT);
    if (stop != null) S.pvT = setInterval(() => { if (PL.time() >= stop - 0.02 || !PL.playing()) { PL.pause(); clearInterval(S.pvT); } }, 25); } };
}
function elPlayer(el, offset, before) {
  return { now: () => offset() + el.currentTime, play: (x, stop) => { const src0 = el.src; if (before) before(x);
    if (el.src !== src0) { el.addEventListener('loadedmetadata', () => { el.currentTime = Math.max(0, x - offset()); el.play().catch(() => {}); }, { once: true }); }
    else { el.currentTime = Math.max(0, x - offset()); el.play().catch(() => {}); } clearInterval(S.pvT);
    if (stop != null) S.pvT = setInterval(() => { if (offset() + el.currentTime >= stop - 0.02 || el.paused) { el.pause(); clearInterval(S.pvT); } }, 25); } };
}
function wireTE(d, pl, onChange) {
  $$('[data-te]', d).forEach(box => {
    const inp = $('input', box), role = box.dataset.role, get = () => parseT(inp.value);
    const preview = x => { if (!pl || x == null) return; role === 'end' ? pl.play(Math.max(0, x - 1.5), x) : pl.play(x, x + 1.5); };
    $$('[data-tn]', box).forEach(b => b.onclick = e => { e.stopPropagation(); const v = get() ?? (pl ? pl.now() : 0); const x = Math.max(0, Math.round((v + +b.dataset.tn) * 100) / 100);
      inp.value = fmtP(x); preview(x); onChange && onChange(); });
    const now = $('[data-tnow]', box), play = $('[data-tplay]', box);
    if (!pl) { now.hidden = play.hidden = true; }
    now.onclick = e => { e.stopPropagation(); inp.value = fmtP(pl.now()); onChange && onChange(); };
    play.onclick = e => { e.stopPropagation(); const x = get(); if (x == null) return; role === 'end' ? pl.play(Math.max(0, x - 2.5), x) : pl.play(x, null); };
    inp.oninput = () => onChange && onChange();
  });
  onChange && onChange();
}
/* a new part: name, start and end — typed, nudged or taken from the player */
async function partSheet(itemId, a, b) {
  const pl = mainPlayer(itemId);
  const r = await sheet(`✂️ ${t('new_part')}`, `<div class="field"><label>${t('part_name')}</label><input id="pn" dir="auto" placeholder="${t('part_name_ph')}"></div>
      ${teHTML('pa', t('start'), a, 'start')}${teHTML('pb', t('end'), b, 'end')}<p class="muted small" id="plen"></p>`,
    `<button class="btn pri big" value="save">✓ ${t('save_only')}</button><button class="btn soft big" value="mp3">⬇ ${t('save_mp3')}</button><button class="btn soft big" value="tr">📝 ${t('save_tr')}</button><button class="btn soft big" value="proj">${PJADD} ${t('save_proj')}</button>`,
    d => { const upd = () => { const x = parseT($('#pa', d).value), y = parseT($('#pb', d).value); $('#plen', d).innerHTML = x != null && y != null && y > x ? `${t('len')}: <bdi dir="ltr">${fmtP(y - x)}</bdi>` : `<span class="warnc">${t('bad_time')}</span>`; };
      wireTE(d, pl, upd); const i = $('#pn', d); setTimeout(() => i.focus(), 60); i.onkeydown = e => { if (e.key === 'Enter') $('button[value=save]', d).click(); }; });
  if (!r || r === 'x') return false;
  const name = $('#pn').value.trim(), x = parseT($('#pa').value), y = parseT($('#pb').value);
  if (x == null || y == null || y <= x) { toast(t('bad_time')); return false; }
  const m = await post(`/api/items/${itemId}/bookmarks`, { name, start: x, end: y });
  if (r === 'mp3' || r === 'tr') { await post('/api/bookmarks/action', { ids: [m.id], action: r === 'mp3' ? 'mp3' : 'transcribe' }); pollJobs(); }
  toast(r === 'save' || r === 'proj' ? t('part_saved') : t('in_tasks'));
  if (S.item && S.item.id === itemId) await refreshItem({ keepTr: true }); else if (PL.item && PL.item.id === itemId) afterMark();
  if (r === 'proj') projectSheet([{ item_id: itemId, start: x, end: y, title: name }], name);
  return true;
}
/* marks always go to the lesson that is playing — from its page or from the mini player anywhere */
const plLesson = () => PL.item && /^\d+$/.test(String(PL.item.id)) ? +PL.item.id : null;
async function afterMark() {
  const id = plLesson();
  if (S.item && S.item.id === id) return refreshItem({ keepTr: true });
  const d = await api('/api/items/' + id).catch(() => null);
  if (d && PL.item && PL.item.id === id) PL.item.bookmarks = d.bookmarks;
}
async function bookmarkHere() {
  if (!PL.ready() || !plLesson()) return toast(t('not_ready'));
  const x = PL.time();
  const r = await post(`/api/items/${plLesson()}/bookmarks`, { start: x });
  await afterMark();
  toast(t('marked_at', fmt(x)), { label: t('name_it'), fn: async () => { const n = await promptText(t('part_name'), '', t('part_name_ph')); if (n) { await patch('/api/bookmarks/' + r.id, { name: n }); afterMark(); } } });
}
function markStart() { if (!PL.ready() || !plLesson()) return toast(t('not_ready')); S.pending = PL.time(); toast('🟢 ' + fmt(S.pending), { label: t('cancel'), fn: () => S.pending = null }); }
async function markEnd() {
  if (!PL.ready() || !plLesson()) return toast(t('not_ready'));
  if (S.pending == null) return toast(t('press_start'));
  const a = S.pending, b = PL.time();
  if (b <= a) return toast(t('end_after'));
  if (PL.playing()) PL.pause();
  if (await partSheet(plLesson(), a, b)) S.pending = null;
}

/* ---------- transcript under the player ---------- */
async function loadTranscript() {
  const box = $('#sb-tr'); if (!box) return;
  const d = S.item;
  if (!d.transcripts.length) { box.innerHTML = `<p class="muted">${t('tr_empty')}</p><button class="btn pri big" data-act="item-action" data-a="transcribe">📝 ${t('tr_full')}</button>`; return; }
  let key = S.tr.key;
  if (key !== 'all' && !d.transcripts.some(x => String(x.id) === String(key))) key = 'all';
  if (d.transcripts.length === 1) key = String(d.transcripts[0].id);
  S.tr.key = key;
  const segs = key === 'all' ? await api(`/api/items/${d.id}/segments`) : (await api('/api/transcripts/' + key)).segments;
  S.tr.segs = segs; S.tr.cur = -1;
  const one = key !== 'all' ? d.transcripts.find(x => String(x.id) === String(key)) : null;
  const heads = [...d.excerpts].filter(x => x.title).sort((a, b) => a.start - b.start); let hi = 0;
  const pick = S.pick;
  box.innerHTML = `
    ${d.transcripts.length > 1 ? `<button class="trpick" data-act="tr-choose"><span class="ico">${IC.doc}</span><span class="grow minw"><small>${t('tr_showing')} · ${d.transcripts.length + 1}</small>
      <b dir="auto">${esc(one ? nice(one.title) : t('tr_all'))}</b>${one && one.end ? `<small>${rng(one.start || 0, one.end)}</small>` : ''}</span><span class="chev">⌄</span></button>` : ''}
    ${pick ? `<div class="banner pickbar"><b class="grow">✂️ ${pick.a == null ? t('pick_first') : t('pick_last')}</b><button class="btn" data-act="pick-cancel">${t('cancel')}</button></div>` : ''}
    <div class="trbar">
      ${S.editTr ? `<button class="btn pri" data-act="tr-save">✓ ${t('done_edit')}</button><button class="btn" data-act="tr-cancel">${t('cancel')}</button>`
        : `<button class="btn soft" data-act="pick-start">✂️ ${t('cut_text')}</button>
           <button class="btn gold" data-act="export" data-src="${one ? 'transcript' : 'item'}" data-tid="${one ? one.id : ''}">⬇ ${t('export_book')}</button>
           <button class="btn" data-act="tr-edit">✏️ ${t('edit')}</button><button class="btn" data-act="tr-copy">📋 ${t('copy')}</button>
           <label class="chip big"><input type="checkbox" data-act="follow" ${S.set.follow !== false ? 'checked' : ''}> ${t('follow')}</label>
           ${one ? `<button class="btn ghost" data-act="tr-rename" data-id="${one.id}">🏷️</button><button class="btn ghost danger" data-act="tr-del" data-id="${one.id}">🗑</button>` : ''}`}
    </div>
    ${S.editTr ? '' : `<div class="trq"><input class="input" id="trq" dir="auto" placeholder="${t('tr_search_ph')}" value="${esc(S.tr.q || '')}" autocomplete="off"><span class="muted small" id="trqN"></span></div>`}
    <div class="trbox ${pick ? 'picking' : ''}" id="trbox">${segs.map((s, i) => {
      let h = '';
      while (hi < heads.length && heads[hi].start <= s.start + 0.5) { h += `<div class="trhead" data-act="seek" data-t="${heads[hi].start}">📌 ${esc(heads[hi].title)}</div>`; hi++; }
      const inPick = pick && pick.a != null && i === pick.a;
      return h + (S.editTr
        ? `<div class="seg" data-i="${i}"><span class="tm"><bdi>${fmt(s.start)}</bdi></span><textarea dir="auto">${esc(s.text)}</textarea></div>`
        : `<div class="seg ${inPick ? 'picked' : ''}" data-i="${i}" data-act="seg" data-t="${s.start}"><span class="tm"><bdi>${fmt(s.start)}</bdi></span><p dir="auto">${esc(s.text)}</p></div>`);
    }).join('')}</div>`;
  const q = $('#trq');
  if (q) { q.oninput = () => { S.tr.q = q.value; clearTimeout(q.t); q.t = setTimeout(trSearch, 150); }; if (S.tr.q) trSearch(); }
}
/* the search box above the transcript: shows only the sentences with the word, the word marked; tap one to jump */
const trNorm = s => String(s || '').replace(/[\u064B-\u0652\u0670\u0640]/g, '').replace(/[أإآ]/g, 'ا').replace(/ة/g, 'ه').replace(/ى/g, 'ي').toLowerCase();
function trSearch() {
  const box = $('#trbox'), n = $('#trqN'); if (!box) return;
  const words = trNorm(S.tr.q).split(/\s+/).filter(Boolean);
  let hits = 0;
  $$('.seg', box).forEach(el => {
    const s = S.tr.segs[+el.dataset.i], p = $('p', el); if (!s || !p) return;
    if (!words.length) { el.hidden = false; p.innerHTML = esc(s.text); return; }
    const ok = words.every(w => trNorm(s.text).includes(w));
    el.hidden = !ok; if (!ok) return;
    hits++;
    // mark the words in the shown text (the text is compared without diacritics, so match on the plain words)
    p.innerHTML = esc(s.text).split(/(\s+)/).map(tok => words.some(w => trNorm(tok).includes(w)) ? `<mark class="hl">${tok}</mark>` : tok).join('');
  });
  $$('.trhead', box).forEach(h => h.hidden = !!words.length);
  if (n) n.textContent = words.length ? (hits ? t('tr_hits', hits) : t('tr_nohit')) : '';
}
let lastUserScroll = 0;
document.addEventListener('scroll', e => { if (e.target && e.target.id === 'trbox') lastUserScroll = Date.now(); }, true);
function followTranscript(x) {
  const segs = S.tr.segs; if (!segs || !segs.length || S.editTr || !S.item || !PL.item || PL.item.id !== S.item.id) return;
  let lo = 0, hi = segs.length - 1, i = -1;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (segs[m].start <= x) { i = m; lo = m + 1; } else hi = m - 1; }
  if (i === S.tr.cur) return;
  const box = $('#trbox'); if (!box) return;
  const old = box.querySelector('.seg.now'); if (old) old.classList.remove('now');
  S.tr.cur = i; if (i < 0) return;
  const el = box.querySelector(`.seg[data-i="${i}"]`); if (!el) return;
  el.classList.add('now');
  if (S.set.follow !== false && PL.playing() && Date.now() - lastUserScroll > 4000) box.scrollTop = el.offsetTop - box.clientHeight / 3;
}
async function finishPick(i) {
  const segs = S.tr.segs, p = S.pick, itemId = S.item.id;
  const a = Math.min(p.a, i), b = Math.max(p.a, i);
  const start = segs[a].start, end = segs[b].end, text = segs.slice(a, b + 1).map(s => s.text).join(' ');
  let title = '';
  S.pick = null; loadTranscript();
  const r = await sheet(`📌 ${t('new_ex')}<br><span class="small muted">${rng(start, end)}</span>`,
    `<div class="field"><label>${t('ex_title')}</label><input id="xt" dir="auto" placeholder="${t('ex_title_ph')}"></div><p class="expreview" dir="auto">${esc(text)}</p>`,
    `<button class="btn pri big" value="save">✓ ${t('save_only')}</button><button class="btn soft big" value="mp3">⬇ ${t('save_mp3')}</button><button class="btn soft big" value="proj">${PJADD} ${t('save_proj')}</button>`,
    d => { const x = $('#xt', d); setTimeout(() => x.focus(), 60); x.oninput = () => title = x.value; });
  if (!r || r === 'x') return;
  const x = await post(`/api/items/${itemId}/excerpts`, { start, end, title: title.trim() });
  if (r === 'mp3') { await post(`/api/excerpts/${x.id}/clip`, { fmt: 'mp3' }); pollJobs(); }
  toast(t('ex_saved'));
  if (S.item && S.item.id === itemId) await refreshItem();
  if (r === 'proj') projectSheet([{ item_id: itemId, start, end, title: title.trim() }], title.trim());
}
function exListHTML() {
  const d = S.item;
  return d.excerpts.length ? `<div class="btns" style="margin-bottom:8px"><button class="chip big gold" data-act="export" data-which="excerpts">📕 ${t('dl_book_all')}</button></div>
    <div class="list">${d.excerpts.map(x => exCard(x, d.jobs, false)).join('')}</div>` : `<p class="muted">${t('ex_empty')}</p>`;
}

/* ---------- benefits / notes ---------- */
function notesHTML() {
  const d = S.item;
  return `${S.noteEdit === 'new' ? noteEditor(null) : `<button class="btn soft big wide" data-act="note-new">＋ ${t('add_note')}</button>`}
    ${d.notes.length ? '' : `<p class="muted small" style="margin-top:10px">${t('notes_empty')}</p>`}
    ${d.notes.map(n => S.noteEdit === n.id ? noteEditor(n) : `<div class="note-card" data-n="${n.id}"><div class="txt" dir="auto">${esc(n.text)}</div>
      <div class="r">${n.time != null ? `<button class="chip gold" data-act="seek" data-t="${n.time}">▶ <bdi>${fmt(n.time)}</bdi></button>` : ''}<div class="grow"></div>
      <button class="btn ghost" data-act="note-edit">✏️</button><button class="btn ghost" data-act="note-copy">📋</button><button class="btn ghost danger" data-act="note-del">🗑</button></div></div>`).join('')}`;
}
function noteEditor(n) {
  const x = n ? n.time : (PL.ready() ? PL.time() : null);
  return `<div class="noteedit" data-n="${n ? n.id : 'new'}"><textarea id="noteTxt" dir="auto" placeholder="${t('note_text_ph')}">${esc(n ? n.text : '')}</textarea>
    <label class="sw"><span>${t('link_time')} ${x != null ? `<b>(<bdi>${fmt(x)}</bdi>)</b>` : ''}</span><input type="checkbox" id="noteT" ${n ? (n.time != null ? 'checked' : '') : 'checked'} data-t="${x ?? ''}"></label>
    <div class="btns"><button class="btn pri big" data-act="note-save">✓ ${t('save')}</button><button class="btn big" data-act="note-cancel">${t('cancel')}</button></div></div>`;
}

/* ---------- files & tools ---------- */
const GROUPS = { clip: ['المقاطع', 'parts'], transcribe: ['التفريغات', 'transcripts'] };
function pendingRow(j) {
  const pct = Math.round((j.progress || 0) * 100);
  const act = j.status === 'error' ? `<button class="btn warn" data-act="job-retry" data-j="${j.id}">↻ ${t('retry')}</button>`
    : j.status === 'paused' ? `<button class="btn pri" data-act="job-op" data-op="resume" data-j="${j.id}">▶</button><button class="btn ghost danger" data-act="job-op" data-op="cancel" data-j="${j.id}">✕</button>`
    : `<button class="btn" data-act="job-op" data-op="pause" data-j="${j.id}">⏸</button><button class="btn ghost danger" data-act="job-op" data-op="cancel" data-j="${j.id}">✕</button>`;
  return `<div class="file pending ${j.status}"><div class="fi">${j.status === 'error' ? '⚠️' : j.status === 'queued' ? '🕒' : '<span class="spin"></span>'}</div>
    <div class="nm"><b dir="auto">${esc(nice(j.title))}</b><small>${t('st_' + j.status)} · <bdi>${pct}%</bdi>${j.eta ? ' · ' + leftTxt(j) : ''}</small>
      ${j.status === 'error' ? `<small class="errtxt" dir="auto">${esc(j.message || '')}</small>` : `<div class="bar thin"><i style="width:${pct}%"></i></div>`}</div>
    <div class="btns nowrap">${act}</div></div>`;
}
function filesHTML() {
  const d = S.item;
  const pend = d.jobs.filter(j => ['running', 'queued', 'paused', 'error'].includes(j.status) && j.kind !== 'info');
  if (!d.files.length && !pend.length) return `<p class="muted">${t('files_empty')}</p>`;
  const groups = {};
  d.files.forEach(f => { const g = f.name.includes('/') ? f.name.split('/')[0] : ''; (groups[g] = groups[g] || []).push(f); });
  const pendIn = {};
  pend.forEach(j => {
    const names = GROUPS[j.kind]; let g = '';
    if (names) g = Object.keys(groups).find(k => names.includes(k)) || names[LANG === 'ar' ? 0 : 1];
    (pendIn[g] = pendIn[g] || []).push(j); if (!groups[g]) groups[g] = [];
  });
  const same = (a, b) => a && b && (a === b || a.endsWith('/' + b) || b.endsWith('/' + a));
  const whenOf = path => {
    const j = d.jobs.find(x => same(x.result, path) && x.params && x.params.start != null);
    const tr = !j && (d.transcripts || []).find(x => same(x.file, path) && (x.bookmark_id || x.start));
    const a = j ? +j.params.start : tr ? +tr.start : null, b = j ? j.params.end : tr ? tr.end : null;
    return a == null ? '' : `<button class="chip when" data-act="play-at" data-item="${d.id}" data-t="${a}">▶ ${b ? rng(a, +b) : `<bdi>${fmt(a)}</bdi>`}</button>`;
  };
  const isClip = path => d.jobs.some(x => x.kind === 'clip' && x.result === path);
  const tookOf = path => { const j = d.jobs.find(x => x.result === path && x.taken); return j ? ` · <span class="okc">${tookTxt(j)}</span>` : ''; };
  const lockOf = path => { const j = d.jobs.find(x => x.kind === 'clip' && x.result === path); const b = j && d.bookmarks.find(m => m.id === j.bookmark_id); return !!(b && b.done); };
  const local = ['localhost', '127.0.0.1'].includes(location.hostname) && !/Android/i.test(navigator.userAgent);
  return (local && d.dir ? `<button class="btn" data-act="open-folder" style="margin-bottom:6px">📂 ${t('open_folder')}</button>` : '') +
    Object.entries(groups).sort((x, y) => (x[0] ? 1 : 0) - (y[0] ? 1 : 0)).map(([g, fs]) => fgroupHTML(g || t('main_folder'), fs.length + (pendIn[g] || []).length,
      (pendIn[g] || []).map(pendingRow).join('') + fs.map(f => fileRow({ path: f.path, name: f.name.split('/').pop().replace(/\.[^.]+$/, ''), size: f.size,
        clip: isClip(f.path), when: whenOf(f.path), took: tookOf(f.path), locked: lockOf(f.path) })).join(''))).join('');
}
/* a folder heading inside Files: tap it to fold or open */
function fgroupHTML(name, n, body) {
  const key = 'fg.' + name, closed = store.get(key, false);
  return `<div class="fgbox ${closed ? 'closed' : ''}"><button class="fgroup" data-act="fgrp" data-k="${esc(key)}"><span class="grow minw" dir="auto">📁 ${esc(name)}</span><span class="n">${n}</span><span class="chev">⌄</span></button>
    <div class="fgbody">${body}</div></div>`;
}
const fileIc = p => /\.(mp3|m4a|opus|ogg|wav)$/i.test(p) ? IC.music : /\.(mp4|webm|mkv|mov)$/i.test(p) ? IC.film : IC.doc;
/* one finished file: the name gets the whole width, the small buttons sit in the bottom corner */
function fileRow(o) {
  const ext = ((o.path || '').match(/\.([^./]+)$/) || ['', ''])[1].toUpperCase();
  const media = /\.(mp3|m4a|opus|ogg|wav|mp4|webm)$/i.test(o.path || '');
  const tap = o.clip ? `data-act="clip-open" data-path="${esc(o.path)}"` : (o.tap || '');
  return `<div class="file2 ${o.clip || o.tap ? 'tapf' : ''} ${o.locked ? 'locked' : ''}"><div class="ftop" ${tap}><span class="fic">${o.icon || fileIc(o.path || '')}</span>
      <div class="fnm"><b dir="auto">${esc(nice(o.name))}${o.locked ? ` <span class="lk">✓ ${t('done_lock')}</span>` : ''}</b>
        <small>${o.sub ? `<span dir="auto">${o.sub}</span> · ` : ''}${ext ? `<span class="chip tiny">${esc(ext)}</span> ` : ''}${o.size != null ? `<bdi>${size(o.size)}</bdi>` : ''}${o.took || ''}</small></div></div>
    <div class="fbar">${o.when || ''}<div class="grow"></div>${o.btns || ''}
      ${media ? `<button class="ibtn" data-act="play-file" data-path="${esc(o.path)}" aria-label="play">${IC.play}</button>` : (o.path && !o.noOpen ? `<a class="ibtn" href="${mediaURL(o.path)}" target="_blank" aria-label="open">${IC.doc}</a>` : '')}
      ${o.clip ? `<button class="ibtn" data-act="clip-proj" data-path="${esc(o.path)}" aria-label="project">${PJADD}</button>` : ''}
      ${o.path ? `<a class="ibtn dl" href="${mediaURL(o.path)}?dl=1" aria-label="download">${IC.dl}</a>` : ''}</div></div>`;
}
function toolsHTML() {
  const d = S.item, online = !!d.url;
  return `<div class="btns grid2">
    ${online && d.media === 'video' ? `<span class="split big"><button class="btn big ${d.file ? '' : 'pri'}" data-act="item-action" data-a="fetch_video" value="x">⬇ ${t('dl_video')}</button>${qdd('video', `data-item="${d.id}"`, 'fetch')}</span>` : ''}
    ${online ? `<button class="btn big" data-act="item-action" data-a="fetch_audio" value="x">⬇ ${t('dl_audio')}</button>` : ''}
    ${d.file && d.media === 'video' ? `<button class="btn big" data-act="item-action" data-a="convert" value="x">🎵 ${t('to_mp3')}</button>` : ''}
    <button class="btn big" data-act="item-action" data-a="transcribe" value="x">📝 ${t('tr_full')}</button>
    <button class="btn big gold" data-act="export" data-which="full" value="x">📕 ${t('export_book')}</button>
    <button class="btn big" data-act="rename-item" value="x">✏️ ${t('rename')}</button>
    <button class="btn big" data-act="move-item" value="x">📁 ${t('move')}</button>
    <button class="btn big danger" data-act="del-item" value="x">🗑 ${t('del_item')}</button></div>`;
}

/* ---------- export: PDF book / TXT / Word, with or without times ---------- */
async function exportSheet(src, id, which, title) {
  const o = store.get('exp2', { fmt: 'pdf', ts: 0, notes: true, cover: true, toc: true, mode: 'auto', size: 'l' });
  let content = which || 'full';
  await sheet('⬇ ' + t('export_book'), `
    <div class="field"><label>${t('exp_format')}</label><div class="fmtcards" data-seg="fmt">
      ${[['pdf', '📕', t('f_pdf')], ['txt', '📃', t('f_txt')], ['docx', '📄', t('f_word')]].map(([v, i, l]) => `<button type="button" data-v="${v}" class="${o.fmt === v ? 'on' : ''}"><i>${i}</i><span>${l}</span></button>`).join('')}</div></div>
    <div class="field"><label>${t('exp_times')}</label>${segc('ts', o.ts ? 1 : 0, [[0, t('no_ts')], [1, '⏱ ' + t('with_ts')]])}</div>
    ${src === 'item' ? `<div class="field"><label>${t('exp_content')}</label>${segc('content', content, [['full', t('exp_full')], ['clips', t('exp_parts')], ['excerpts', t('exp_ex')], ['both', t('exp_both')]])}</div>` : ''}
    <div class="field"><label>🔤 ${t('exp_font')}</label>${fontSeg('font', o.font || S.set.font_read || 'amiri', 'data-seg')}</div>
    ${paraScope(src, id, content) ? `<div class="field" id="paraF"><button type="button" class="btn soft wide" id="exParas">✏️ ${t('edit_paras')}</button><small id="paraOwn"></small></div>` : ''}
    <div class="field" id="sizeF"><label>${t('exp_size')}</label>${segc('size', o.size, [['m', t('medium')], ['l', t('large')], ['xl', t('xlarge')], ['xxl', t('huge')]])}</div>
    <div class="field"><label>${t('exp_title')}</label><input id="ex_title" dir="auto" value="${esc(nice(title || ''))}"></div>
    <details class="more"><summary>${t('exp_more')}</summary>
      <div class="field"><label>${t('exp_sub')}</label><input id="ex_sub" dir="auto"></div>
      <div class="field"><label>${t('exp_author')}</label><input id="ex_author" dir="auto" value="${esc(store.get('exp_author', ''))}"></div>
      <div class="field"><label>${t('exp_hfont')}</label>${fontSeg('hfont', o.hfont || o.font || S.set.font_read || 'amiri', 'data-seg')}</div>
      <div class="field"><label>${t('exp_style')}</label>${segc('mode', o.mode, [['auto', t('exp_paras')], ['lines', t('exp_lines')]])}</div>
      ${src !== 'project' ? `<label class="sw"><span>${t('exp_notes')}</span><input type="checkbox" id="ex_notes" ${o.notes ? 'checked' : ''}></label>` : ''}
      <label class="sw"><span>${t('exp_cover')}</span><input type="checkbox" id="ex_cover" ${o.cover ? 'checked' : ''}></label>
      <label class="sw"><span>${t('exp_toc')}</span><input type="checkbox" id="ex_toc" ${o.toc ? 'checked' : ''}></label></details>
    <p class="muted small" id="pdfHint">${t('pdf_hint')}</p>`,
    `<button class="btn ghost" id="exPrev">👁 ${t('preview')}</button><button class="btn pri big" id="exGo">⬇ ${t('exp_go')}</button>`, (d, close) => {
      const sync = () => { $('#pdfHint', d).hidden = o.fmt !== 'pdf'; $('#sizeF', d).hidden = o.fmt === 'txt'; $('#exGo', d).innerHTML = o.fmt === 'pdf' ? '📕 ' + t('exp_go_pdf') : '⬇ ' + t('exp_go'); };
      wireSegc(d, (k, v) => { if (k === 'content') content = v; else if (k === 'ts') o.ts = +v; else o[k] = v; sync();
        if ($('#paraF', d)) $('#paraF', d).hidden = !paraScope(src, id, content); });
      sync();
      if ($('#exParas', d)) {
        api('/api/paras?scope=' + encodeURIComponent(paraScope(src, id, 'full'))).then(r => { if (r.custom && $('#paraOwn', d)) $('#paraOwn', d).textContent = t('paras_own'); }).catch(() => {});
        $('#exParas', d).onclick = () => { store.set('exp2', o); close('x'); paraEditor(paraScope(src, id, 'full'), () => exportSheet(src, id, content, title)); };
      }
      const url = f => {
        const g = s => $(s, d);
        o.cover = g('#ex_cover').checked; o.toc = g('#ex_toc').checked; if (g('#ex_notes')) o.notes = g('#ex_notes').checked;
        store.set('exp2', o); store.set('exp_author', g('#ex_author').value);
        return '/export?' + new URLSearchParams({ src, id, which: content, ts: o.ts ? 1 : 0, notes: o.notes ? 1 : 0, cover: o.cover ? 1 : 0, toc: o.toc ? 1 : 0,
          mode: o.mode, size: o.size, font: o.font || S.set.font_read || 'amiri', hfont: o.hfont || o.font || S.set.font_read || 'amiri', title: g('#ex_title').value, subtitle: g('#ex_sub').value, author: g('#ex_author').value, fmt: f });
      };
      $('#exPrev', d).onclick = () => window.open(url('html'), '_blank');
      $('#exGo', d).onclick = () => { if (o.fmt === 'pdf') window.open(url('html') + '&print=1', '_blank'); else download(url(o.fmt)); close('ok'); };
    });
}

const paraScope = (src, id, content) => src === 'transcript' ? 'tr:' + id : src === 'item' && content === 'full' ? 'item:' + id : null;
/* name every paragraph and set where it starts and ends — used by PDF, Word and text */
async function paraEditor(scope, back) {
  const r0 = await api('/api/paras?scope=' + encodeURIComponent(scope));
  const ps = r0.paras.map(p => ({ ...p })), segs = r0.segs;
  const prev = p => segs.filter(x => p.start - 0.05 <= (x.start + x.end) / 2 && (x.start + x.end) / 2 < p.end + 0.05).map(x => x.text).join(' ');
  const row = (p, i) => `<div class="pedit" data-i="${i}"><div class="pe1"><span class="num">${i + 1}</span><input class="grow" dir="auto" data-f="title" value="${esc(p.title || '')}" placeholder="${t('para_title_ph')}"><button type="button" class="btn ghost danger" data-del="${i}">🗑</button></div>
      <div class="pe2" dir="ltr"><input data-f="start" value="${fmt(p.start)}" inputmode="decimal"><span>–</span><input data-f="end" value="${fmt(p.end)}" inputmode="decimal"></div>
      <p class="pe3" dir="auto">${esc(prev(p).slice(0, 150))}…</p></div>`;
  const r = await sheet('✏️ ' + t('edit_paras'), `<p class="muted small">${t('paras_p')}</p><div id="pes"></div>
      <div class="btns" style="margin-top:8px"><button type="button" class="btn soft" id="peAdd">＋ ${t('add_para')}</button>${r0.custom ? `<button type="button" class="btn ghost" id="peReset">↺ ${t('paras_auto')}</button>` : ''}</div>`,
    `<button class="btn big" value="no">${t('cancel')}</button><button class="btn pri big" value="ok">✓ ${t('save')}</button>`, (d, close) => {
      const box = $('#pes', d), draw = () => box.innerHTML = ps.map(row).join('');
      draw();
      box.addEventListener('input', e => { const el = e.target.closest('.pedit'); if (!el) return; const p = ps[+el.dataset.i], f = e.target.dataset.f;
        if (f === 'title') p.title = e.target.value; else { const v = parseT(e.target.value); if (v != null) { p[f] = v; $('.pe3', el).textContent = prev(p).slice(0, 150) + '…'; } } });
      box.addEventListener('click', e => { const x = e.target.closest('[data-del]'); if (x) { e.stopPropagation(); ps.splice(+x.dataset.del, 1); draw(); } });
      $('#peAdd', d).onclick = e => { e.stopPropagation(); const last = ps[ps.length - 1], a = last ? last.end : 0; ps.push({ title: '', start: a, end: a + 60 }); draw(); box.lastElementChild.scrollIntoView({ behavior: 'smooth' }); };
      if ($('#peReset', d)) $('#peReset', d).onclick = e => { e.stopPropagation(); close('reset'); };
    });
  if (r === 'reset') { await post('/api/paras', { scope, paras: null }); return paraEditor(scope, back); }
  if (r === 'ok') { await post('/api/paras', { scope, paras: ps }); toast(t('saved')); }
  if (back) back();
}

/* ---------- projects: add clips / lessons ---------- */
async function projectSheet(clips, defTitle) {
  const ps = await api('/api/projects');
  const last = store.get('lastProject', ps[0] ? ps[0].id : '');
  await sheet('💼 ' + t('to_project'), `
    <div class="field"><label>${t('choose_project')}</label><select id="pj">${ps.map(p => `<option value="${p.id}" ${String(p.id) === String(last) ? 'selected' : ''}>💼 ${esc(p.name)}</option>`).join('')}
      <option value="new" ${ps.length ? '' : 'selected'}>＋ ${t('new_project')}…</option></select></div>
    <div class="field" id="pjNewF" ${ps.length ? 'hidden' : ''}><label>${t('project_name')}</label><input id="pjNew" dir="auto" placeholder="${t('project_name')}"></div>
    <div class="field" id="pjSecF"><label>📁 ${t('sub_opt')}</label><select id="pjSec"></select></div>
    ${clips.length === 1 ? `<div class="field"><label>${t('clip_title')}</label><input id="pjTitle" dir="auto" value="${esc(defTitle || clips[0].title || '')}"></div>
      ${teHTML('pjA', t('start'), clips[0].start, 'start')}${teHTML('pjB', t('end'), clips[0].end, 'end')}` : `<p class="muted">${t('clips_n', clips.length)}</p>`}`,
    `<button class="btn pri big wide" id="pjGo">＋ ${t('add')}</button>`, (d, close) => {
      const sel = $('#pj', d);
      if (clips.length === 1) wireTE(d, mainPlayer(clips[0].item_id));
      const secs = () => { const p = ps.find(x => String(x.id) === sel.value); let l = []; try { l = JSON.parse((p && p.sections) || '[]'); } catch (e) {}
        $('#pjSec', d).innerHTML = `<option value="">📄 ${t('no_sub')}</option>` + l.map(x => `<option value="${esc(x)}">📁 ${esc(x)}</option>`).join('') + `<option value="__new">📁＋ ${t('new_sub')}…</option>`; };
      secs(); sel.onchange = () => { $('#pjNewF', d).hidden = sel.value !== 'new'; secs(); };
      $('#pjGo', d).onclick = async () => {
        let pid = sel.value, pname = sel.selectedOptions[0].textContent.replace('💼 ', '');
        if (pid === 'new') { pname = $('#pjNew', d).value.trim() || t('new_project'); pid = (await post('/api/projects', { name: pname })).id; }
        if (clips.length === 1) {
          const a = parseT($('#pjA', d).value), b = parseT($('#pjB', d).value);
          if (a == null || b == null || a === undefined || b === undefined || b <= a) return toast(t('bad_time'));
          clips[0] = { ...clips[0], start: a, end: b, title: $('#pjTitle', d).value.trim() };
        }
        let section = $('#pjSec', d).value;
        if (section === '__new') { section = (prompt(t('new_sub')) || '').trim(); }
        if (section) { const p = (await api('/api/projects/' + pid)); if (!p.sections.includes(section)) await patch('/api/projects/' + pid, { sections: [...p.sections, section] }); }
        for (const c of clips) await post(`/api/projects/${pid}/clips`, { ...c, section });
        store.set('lastProject', pid); close('ok'); toast(t('added_to', pname));
      };
    });
}
async function itemProjectsSheet(item) {
  const ps = await api('/api/projects'); let chosen = new Set(item.projects);
  const r = await sheet('💼 ' + t('in_projects'), `<div class="list">${ps.map(p => `<label class="li check"><input type="checkbox" data-p="${p.id}" ${chosen.has(p.id) ? 'checked' : ''}><div class="tt"><b dir="auto">${esc(p.name)}</b></div></label>`).join('')}
    <div class="field" style="margin-top:8px"><label>＋ ${t('new_project')}</label><input id="npj" dir="auto" placeholder="${t('project_name')}"></div></div>`,
    `<button class="btn pri big wide" value="ok">✓ ${t('save')}</button>`);
  if (r !== 'ok') return;
  const now = new Set($$('#sheet [data-p]').filter(x => x.checked).map(x => +x.dataset.p));
  const np = $('#npj').value.trim(); if (np) now.add((await post('/api/projects', { name: np })).id);
  for (const p of now) if (!chosen.has(p)) await post(`/api/projects/${p}/items`, { item_id: item.id });
  for (const p of chosen) if (!now.has(p)) await del(`/api/projects/${p}/items/${item.id}`);
  toast(t('saved')); refreshItem({ keepTr: true });
}
async function projectLessonsSheet(p) {
  await loadLib(); const have = new Set(p.items.map(i => i.id));
  const r = await sheet('🎧 ' + t('add_lessons'), `<div class="list">${S.items.map(i => `<label class="li check"><input type="checkbox" data-i="${i.id}" ${have.has(i.id) ? 'checked' : ''}><div class="th" style="width:54px;height:38px;${i.thumb ? `background-image:url('${esc(i.thumb)}')` : ''}">${i.thumb ? '' : itemIcon(i)}</div><div class="tt"><b dir="auto">${esc(nice(i.title))}</b></div></label>`).join('')}</div>`,
    `<button class="btn pri big wide" value="ok">✓ ${t('save')}</button>`);
  if (r !== 'ok') return;
  const now = new Set($$('#sheet [data-i]').filter(x => x.checked).map(x => +x.dataset.i));
  for (const i of now) if (!have.has(i)) await post(`/api/projects/${p.id}/items`, { item_id: i });
  for (const i of have) if (!now.has(i)) await del(`/api/projects/${p.id}/items/${i}`);
  vProject(p.id);
}

/* ================= search ================= */
function hlRx(words) {
  const cls = { 'ا': '[اأإآٱ]', 'ه': '[هة]', 'ي': '[يىئ]', 'و': '[وؤ]' };
  const w = words.flatMap(p => p.split(/\s+/)).filter(Boolean).map(x => [...x].map(ch => (cls[ch] || ch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) + '[\\u064B-\\u065F\\u0670\\u0640]*').join(''));
  return w.length ? new RegExp('(' + w.join('|') + ')', 'gi') : null;
}
const hl = (txt, rx) => rx ? esc(txt).replace(rx, '<mark class="hl">$1</mark>') : esc(txt);
async function vSearch() {
  await loadLib();
  let scope = store.get('scope', 'all');
  if (!['all', 'none'].includes(String(scope)) && !S.folders.some(f => String(f.id) === String(scope))) { scope = 'all'; store.set('scope', 'all'); }
  view().innerHTML = `
    <div class="h"><h2>🔎 ${t('search_title')}</h2><p>${t('search_p')}</p></div>
    <form id="sf" class="searchform"><div class="search-big"><input class="input" id="sq" dir="auto" placeholder="${t('search_ph')}" value="${esc(S.q)}" enterkeyhint="search"></div>
      <div class="btns nowrap"><select class="input grow" id="sscope"><option value="all">${t('everywhere')}</option>${S.folders.map(f => `<option value="${f.id}" ${String(scope) === String(f.id) ? 'selected' : ''}>${esc((f.icon || '📁') + ' ' + f.name)}</option>`).join('')}</select>
      <button class="btn pri big">🔎 ${t('go')}</button></div></form>
    <div id="sres"></div>`;
  $('#sf').onsubmit = e => { e.preventDefault(); S.q = $('#sq').value; store.set('scope', $('#sscope').value); runSearch(); };
  if (S.q) runSearch(); else setTimeout(() => $('#sq').focus(), 100);
}
async function runSearch() {
  const box = $('#sres'); box.innerHTML = '<p class="muted"><span class="spin"></span></p>';
  let scope = store.get('scope', 'all');
  if (!['all', 'none'].includes(String(scope)) && !S.folders.some(f => String(f.id) === String(scope))) { scope = 'all'; store.set('scope', 'all'); }
  const r = await api(`/api/search?q=${encodeURIComponent(S.q)}&folder=${scope}`);
  S.res = r;
  const rx = hlRx(r.words || []), total = r.results.reduce((a, x) => a + x.hits.length, 0);
  box.innerHTML = `
    ${r.untranscribed ? `<div class="banner warn"><span class="grow minw">⚠️ ${t('untr_n', r.untranscribed)}</span><button class="btn warn" data-act="folder-tr" data-id="${scope}">📝 ${t('tr_them')}</button></div>` : ''}
    ${S.q ? `<div class="toolbar"><b>${t('results_n', total, r.results.length)}</b><div class="grow"></div>${total ? `<button class="btn soft" data-act="res-all-proj">➕ ${t('add_all_proj')}</button>` : ''}</div>` : ''}
    ${r.results.map((x, ri) => `<div class="card rescard"><a class="rh" href="#/item/${x.item_id}"><div class="th" style="width:56px;height:40px;${x.thumb ? `background-image:url('${esc(x.thumb)}')` : ''}">${x.thumb ? '' : itemIcon(x)}</div>
      <b dir="auto" class="grow minw ell">${esc(nice(x.title))}</b><span class="chip acc">${x.hits.length}</span></a>
      <div class="rb">${x.hits.map((h, hi2) => `<div class="hit" data-r="${ri}" data-h="${hi2}"><span class="chip gold">⏱ ${rng(h.start, h.end)}</span>
        <p dir="auto"><span class="ctx">${esc(h.before)} </span>${hl(h.text, rx)}<span class="ctx"> ${hl(h.after, rx)}</span></p>
        <div class="btns"><button class="btn pri" data-act="play-at" data-item="${x.item_id}" data-t="${h.start}">▶ ${t('listen')}</button><button class="btn" data-act="hit-proj">${PJADD} ${t('to_project')}</button>
          <button class="btn" data-act="hit-ex">📌 ${t('excerpt')}</button><button class="btn" data-act="hit-mark">🔖 ${t('mark_here')}</button></div></div>`).join('')}</div></div>`).join('')}
    ${S.q && !total ? `<div class="empty"><div class="big">🔍</div><p>${t('no_results')}</p></div>` : ''}`;
}
const hitClip = (x, h) => ({ item_id: x.item_id, start: Math.max(0, h.start - (+S.set.pad_before || 0)), end: h.end + (+S.set.pad_after || 0), title: S.q.split(/[,،]/)[0].trim() });

/* ================= projects ================= */
async function vProjects() {
  const ps = await api('/api/projects');
  view().innerHTML = `
    <div class="h"><h2>💼 ${t('projects')}</h2><p>${t('proj_p')}</p></div>
    <div class="toolbar"><button class="btn pri big" data-act="new-project">＋ ${t('new_project')}</button></div>
    <div class="list">${ps.map(p => `<a class="li" href="#/project/${p.id}"><div class="th">💼</div><div class="tt"><b dir="auto">${esc(p.name)}</b>
      <small><span>🎧 ${t('lessons_n', p.items)}</span><span>✂️ ${t('clips_n', p.clips)}</span><span>⏱ <bdi>${fmt(p.seconds)}</bdi></span></small>${p.description ? `<small dir="auto" class="ell">${esc(p.description)}</small>` : ''}</div></a>`).join('')
      || `<div class="empty"><div class="big">💼</div><p>${t('proj_empty')}</p></div>`}</div>`;
}
async function vProject(id) {
  const p = await api('/api/projects/' + id).catch(() => null);
  if (!p) { location.hash = '#/projects'; return; }
  S.project = p;
  const j = p.jobs[0], secs = p.clips.reduce((a, c) => a + (c.end - c.start), 0);
  view().innerHTML = `
    <div class="crumbs"><a href="#/projects">${t('projects')}</a> ${SEP()}</div>
    <div class="itemhead"><div class="titlebox"><h2 class="t" dir="auto" data-act="rename-project">${esc(p.name)} <span class="muted small noico">${ICON('pencil')}</span></h2></div></div>
    <div class="field"><textarea class="input" dir="auto" data-edit="project-desc" placeholder="${t('desc_ph')}" style="min-height:64px">${esc(p.description || '')}</textarea></div>
    <div class="stat"><div><b>${p.items.length}</b><small>${t('tab_lessons')}</small></div><div><b>${p.clips.length}</b><small>${t('proj_clips')}</small></div><div><b><bdi>${fmt(secs)}</bdi></b><small>${t('total')}</small></div></div>
    <div class="card pad" style="margin:14px 0">
      <div class="btns"><button class="btn pri big" data-act="proj-zip" ${p.clips.length ? '' : 'disabled'}>⬇ ${t('dl_all_zip')}</button>
        <button class="btn gold big" data-act="export" data-src="project">📕 ${t('export_book')}</button>
        <div class="grow"></div><button class="btn ghost danger" data-act="del-project">🗑</button></div>
      <div id="pjob">${j ? projJobHTML(j) : ''}</div></div>
    ${secHTML('p-lessons', '🎧', t('proj_lessons'), p.items.length, `<div class="btns" style="margin-bottom:8px"><button class="btn soft big" data-act="proj-lessons">＋ ${t('add_lessons')}</button></div>
      <div class="list">${p.items.map(itemRow).join('')}</div>`)}
    ${secHTML('p-clips', '✂️', t('proj_clips'), p.clips.length, projClipsHTML(p))}`;
}

/* clips of a project, grouped in optional sub-folders */
function projClipsHTML(p) {
  let n = 0;
  const card = c => { n++; return `
      <div class="pclip" data-c="${c.id}"><div class="num">${n}</div><div class="body">
        <input class="nm" dir="auto" data-edit="pclip-title" value="${esc(c.title)}" placeholder="${t('untitled')}">
        <div class="chips"><button class="chip acc ell" data-act="play-at" data-item="${c.item_id}" data-t="${c.start}" dir="auto">▶ ${esc(nice(c.item_title || '?'))}</button><button class="chip gold" data-act="pclip-times">⏱ ${rng(c.start, c.end)}</button>
          ${p.sections.length ? `<button class="chip" data-act="pclip-sec">📁 ${esc(c.section || t('no_sub'))}</button>` : ''}</div>
        ${c.excerpt ? `<div class="ex" dir="auto">${esc(c.excerpt)}…</div>` : ''}
        <textarea class="note" dir="auto" data-edit="pclip-note" placeholder="${t('note_ph')}">${esc(c.note || '')}</textarea></div>
        <div class="mv"><button class="btn ghost" data-act="pclip-move" data-d="-1">▲</button><button class="btn ghost" data-act="pclip-move" data-d="1">▼</button><button class="btn ghost danger" data-act="pclip-del">🗑</button></div></div>`; };
  const loose = p.clips.filter(c => !c.section || !p.sections.includes(c.section));
  const tools = `<div class="btns" style="margin-bottom:8px"><button class="btn soft" data-act="psec-new">📁＋ ${t('new_sub')}</button></div>`;
  if (!p.clips.length && !p.sections.length) return tools + `<div class="empty"><div class="big">➕</div><p>${t('proj_clips_empty')}</p><a class="btn pri" href="#/search">🔎 ${t('search')}</a></div>`;
  return tools + (loose.length ? (p.sections.length ? `<div class="psec"><b>📄 ${t('no_sub')}</b></div>` : '') + loose.map(card).join('') : '')
    + p.sections.map(sec => { const cs = p.clips.filter(c => c.section === sec); return `
      <details class="psecbox" open><summary class="psec"><b dir="auto">📁 ${esc(sec)}</b><span class="count">${cs.length}</span><div class="grow"></div>
        <button class="btn ghost" data-act="psec-ren" data-s="${esc(sec)}">✏️</button><button class="btn ghost danger" data-act="psec-del" data-s="${esc(sec)}">🗑</button></summary>
        ${cs.map(card).join('') || `<p class="muted small">${t('sub_empty')}</p>`}</details>`; }).join('');
}
async function pickSection(p, cur) {
  const r = await sheet('📁 ' + t('move_to_sub'), `<div class="list">${[['', '📄 ' + t('no_sub')], ...p.sections.map(x => [x, '📁 ' + x])].map(([v, l]) =>
    `<button class="li" value="s:${esc(v)}" style="width:100%;text-align:start;${(cur || '') === v ? 'border-color:var(--acc);border-width:2px' : ''}"><div class="tt"><b dir="auto">${esc(l)}</b></div></button>`).join('')}
    <button class="li" value="new" style="width:100%;text-align:start"><div class="tt"><b>📁＋ ${t('new_sub')}</b></div></button></div>`);
  if (!r || r === 'x') return undefined;
  if (r === 'new') { const n = await promptText(t('new_sub'), '', t('sub_ph')); if (!n) return undefined; await patch('/api/projects/' + p.id, { sections: [...p.sections, n] }); return n; }
  return r.slice(2);
}
function projJobHTML(j) {
  if (j.status === 'done' && j.result) return `<div class="btns" style="margin-top:12px"><a class="btn ok big wide" href="${mediaURL(j.result)}?dl=1">✅ ${t('zip_ready')}${j.taken ? ` · ${tookTxt(j)}` : ''}</a></div>`;
  return `<div style="margin-top:10px"><span class="st ${j.status}">${t('st_' + j.status)}</span> <span class="muted small">${esc(j.message || '')}</span>
    ${j.status === 'running' ? `<div class="bar"><i style="width:${Math.round(j.progress * 100)}%"></i></div>` : ''}${j.eta ? `<div class="eta">⏱ ${leftTxt(j)}</div>` : ''}</div>`;
}


/* ---------- a finished part in its own window: listen, rename, change times, transcribe, add to a project ---------- */
async function clipSheet(path) {
  let c; try { c = await post('/api/clipfile', { path, action: 'info' }); } catch (e) { return toast(e.message); }
  if (PL.playing()) PL.pause();
  const vid = /\.(mp4|webm|mkv|mov)$/i.test(path), name0 = c.name || path.split('/').pop().replace(/\.[^.]+$/, '');
  const refresh = () => { if (S.item) refreshItem({ keepTr: true }); else if (/^#\/lib\/f\//.test(location.hash)) route(); pollJobs(); };
  await sheet('🎬 ' + t('clip_win'), `
    ${c.src ? `<div class="segc clipsw" style="margin-bottom:8px"><button type="button" data-cm="clip" class="on">🎬 ${t('v_clip')}</button><button type="button" data-cm="src">📖 ${t('v_src')}</button></div>` : ''}
    <${vid || c.media === 'video' ? 'video playsinline' : 'audio'} class="clipmedia" controls autoplay src="${mediaURL(path)}"></${vid || c.media === 'video' ? 'video' : 'audio'}>
    <div class="cliptime" dir="ltr"><span id="cpos">0:00.00</span></div>
    <div class="field"><label>${t('part_name')}</label><div class="btns nowrap"><input id="cn" class="grow" dir="auto" value="${esc(name0)}"><button type="button" class="btn pri" id="cnSave">✓</button></div></div>
    <p class="muted small" dir="auto">🎧 ${esc(nice(c.item_title || ''))}</p>
    <div class="field"><label>${t('edit_times')}</label>${teHTML('ca', t('start'), c.start || 0, 'start')}${teHTML('cb', t('end'), c.end, 'end')}
      <p class="muted small" id="clen"></p><button type="button" class="btn big wide pri" id="cRecut">✂️ ${t('recut')}</button></div>
    <div class="btns grid2">
      <button type="button" class="btn big" id="cTr">📝 ${t('transcribe')}</button>
      <button type="button" class="btn big" id="cProj">${PJADD} ${t('to_project')}</button>
      <button type="button" class="btn big" id="cGo">▶ ${t('in_lesson')}</button>
      <a class="btn big" href="${mediaURL(path)}?dl=1">⬇ ${t('save_file')}</a>
    </div>
    <button type="button" class="btn ghost danger" id="cDel" style="margin-top:8px">🗑 ${t('del_file')}</button>`, '', (d, close) => {
    const med = $('.clipmedia', d); let mode = 'clip';
    const off = () => mode === 'clip' ? (c.start || 0) : 0;
    const setMode = (m, at) => { if (m === mode || (m === 'src' && !c.src)) return; const abs = at != null ? at : off() + med.currentTime; mode = m;
      med.src = mediaURL(m === 'clip' ? path : c.src); med.addEventListener('loadedmetadata', () => { med.currentTime = Math.max(0, abs - off()); }, { once: true });
      $$('[data-cm]', d).forEach(b => b.classList.toggle('on', b.dataset.cm === m)); };
    $$('[data-cm]', d).forEach(b => b.onclick = e => { e.stopPropagation(); setMode(b.dataset.cm); });
    const tick = setInterval(() => { if (!d.open) return clearInterval(tick); $('#cpos', d).textContent = fmtP(off() + med.currentTime); }, 100);
    // times outside the ready part need the whole lesson: switch to it by itself
    const pl = elPlayer(med, off, x => { if (mode === 'clip' && c.src && (x < (c.start || 0) || x > (c.end || 1e9) - 0.05)) { mode = 'src'; med.src = mediaURL(c.src); $$('[data-cm]', d).forEach(b => b.classList.toggle('on', b.dataset.cm === 'src')); } });
    wireTE(d, pl, () => { const x = parseT($('#ca', d).value), y = parseT($('#cb', d).value); $('#clen', d).innerHTML = x != null && y != null && y > x ? `${t('len')}: <bdi dir="ltr">${fmtP(y - x)}</bdi>` : `<span class="warnc">${t('bad_time')}</span>`; });
    if (c.locked) { ['#cn', '#cnSave', '#ca', '#cb', '#cRecut', '#cDel'].forEach(q => $(q, d).disabled = true); $$('[data-tn],[data-tnow]', d).forEach(b => b.disabled = true);
      $('#cRecut', d).insertAdjacentHTML('afterend', `<p class="okc small">✓ ${t('locked_msg')}</p>`); }
    d.addEventListener('close', () => $$('.clipmedia', d).forEach(m => m.pause()), { once: true });
    $('#cnSave', d).onclick = async () => {
      const n = $('#cn', d).value.trim(); if (!n) return;
      const r = await post('/api/clipfile', { path, action: 'rename', name: n }); path = r.path; c.name = n;
      const m = $('.clipmedia', d), at = m.currentTime; m.src = mediaURL(path); m.currentTime = at; toast(t('saved')); refresh();
    };
    $('#cn', d).onkeydown = e => { if (e.key === 'Enter') $('#cnSave', d).click(); };
    $('#cRecut', d).onclick = async () => {
      const a = parseT($('#ca', d).value), b = parseT($('#cb', d).value);
      if (a == null || b == null || b <= a) return toast(t('bad_time'));
      await post('/api/clipfile', { path, action: 'recut', start: a, end: b }); close('x'); toast(t('in_tasks')); refresh();
    };
    $('#cTr', d).onclick = async () => { await post('/api/clipfile', { path, action: 'transcribe' }); close('x'); toast(t('in_tasks')); refresh(); };
    $('#cProj', d).onclick = () => { close('x'); projectSheet([{ item_id: c.item_id, start: c.start, end: c.end, title: c.name || name0 }], c.name || name0); };
    $('#cGo', d).onclick = () => { close('x'); playAt(c.item_id, c.start || 0); };
    $('#cDel', d).onclick = async () => { close('x'); if (await ask(t('del_file_q'), t('delete'), true)) { await post('/api/clipfile', { path, action: 'delete' }); refresh(); } };
  });
}

/* ================= tasks ================= */
async function vTasks(tab) {
  S.ttab = tab === 'done' ? 'done' : 'now';
  view().innerHTML = `<div class="h"><h2>⏳ ${t('tasks')}</h2><div class="grow"></div><button class="ib more" data-act="tasks-menu" aria-label="${t('more_opts')}">${ICON('dots')}</button></div>
    <div class="ftabs" id="ttabs"></div><div id="jobs"></div>`;
  await pollJobs(); renderJobs();
}
function renderJobs() {
  const box = $('#jobs'); if (!box) return;
  const isDone = j => j.status === 'done' || j.status === 'cancelled', now = S.jobs.filter(j => !isDone(j)), done = S.jobs.filter(isDone);
  const tt = $('#ttabs'); if (tt) tt.innerHTML = `<a href="#/tasks" class="${S.ttab !== 'done' ? 'on' : ''}">${t('t_now')} <small>${now.length || ''}</small></a><a href="#/tasks/done" class="${S.ttab === 'done' ? 'on' : ''}">${t('t_done')} <small>${done.length || ''}</small></a>`;
  const list = S.ttab === 'done' ? done : now;
  box.innerHTML = (S.ttab === 'done' && done.length ? `<a class="btn soft wide" href="#/works" style="margin-bottom:10px">📦 ${t('my_works')}</a>` : '') + list.map(j => {
    const pct = Math.round((j.progress || 0) * 100);
    const b = j.status === 'running' || j.status === 'queued' ? `<button class="btn" data-act="job" data-op="pause">⏸ ${t('pause')}</button><button class="btn ghost danger" data-act="job" data-op="cancel">✕ ${t('cancel')}</button>`
      : j.status === 'paused' ? `<button class="btn pri" data-act="job" data-op="resume">▶ ${t('resume')}</button><button class="btn ghost danger" data-act="job" data-op="cancel">✕ ${t('cancel')}</button>`
      : j.status === 'error' ? `<button class="btn warn" data-act="job" data-op="retry">↻ ${t('retry')}</button>`
      : j.status === 'done' && j.result ? `${/\.(mp3|m4a|mp4|webm)$/i.test(j.result) ? `<button class="btn ok" data-act="play-file" data-path="${esc(j.result)}">▶</button>` : ''}<a class="btn ok" href="${mediaURL(j.result)}?dl=1">⬇ ${t('save_file')}</a>${j.item_id ? `<a class="btn" href="#/item/${j.item_id}">${t('show')}</a>` : ''}` : '';
    return `<div class="job ${j.status} ${j.item_id ? 'tap' : ''}" data-j="${j.id}" ${j.item_id ? `data-item="${j.item_id}"` : ''}><div class="jt"><b dir="auto">${esc(nice(j.title))}</b><span class="st ${j.status}">${t('st_' + j.status)}</span></div>
      ${j.status === 'running' || (j.status === 'paused' && pct) ? `<div class="bar"><i style="width:${pct}%"></i></div>` : ''}
      <div class="msg" dir="auto">${esc(j.message || '')}</div>${j.eta || j.taken ? `<div class="eta">⏱ ${j.status === 'done' ? tookTxt(j) : leftTxt(j)}</div>` : ''}${b ? `<div class="btns">${b}</div>` : ''}</div>`;
  }).join('') || `<div class="empty"><div class="big">${S.ttab === 'done' ? '✅' : '⏳'}</div><p>${t(S.ttab === 'done' ? 'no_done' : 'no_tasks')}</p></div>`;
}
let lastSig = '', doneSeen = null;
async function pollJobs() {
  let js; try { js = await api('/api/jobs'); } catch (e) { return; }
  S.jobs = js; renderTabs();
  const done = new Set(js.filter(j => j.status === 'done').map(j => j.id));
  const fresh = doneSeen ? js.filter(j => j.status === 'done' && !doneSeen.has(j.id)) : [];
  doneSeen = done;
  if (fresh.length === 1) toast('✅ ' + nice(fresh[0].title));
  else if (fresh.length > 1) toast('✅ ' + fresh.length);
  if (/^#\/tasks/.test(location.hash)) renderJobs();
  if (/^#\/home/.test(location.hash)) renderHomeJobs();
  if (S.item) {
    const mine = js.filter(j => j.item_id === S.item.id);
    const sig = mine.map(j => j.id + j.status + Math.round((j.progress || 0) * 20)).join('|');
    if (sig !== lastSig) { lastSig = sig; refreshItem({ keepTr: !fresh.some(j => j.kind === 'transcribe' && j.item_id === S.item.id), soft: true }); }
  }
  const libDl = js.filter(j => ['fetch', 'info'].includes(j.kind) && j.status === 'running').map(j => j.id + ':' + Math.round((j.progress || 0) * 10)).join(',');
  if (/^#\/lib/.test(location.hash) && !pollJobs.busy && (fresh.length || libDl !== pollJobs.libSig)) {
    pollJobs.libSig = libDl;
    const act = document.activeElement;
    if (!(act && /INPUT|TEXTAREA|SELECT/.test(act.tagName))) { pollJobs.busy = true; const y = scrollY; try { await route(); scrollTo(0, y); } finally { pollJobs.busy = false; } }
  }
  if (/^#\/project\//.test(location.hash) && S.project) {
    const pj = js.find(j => j.kind === 'project' && j.project_id === S.project.id);
    if (pj) { const b = $('#pjob'); if (b) b.innerHTML = projJobHTML(pj); }
  }
}
/* tasks are checked every 1.5 s while something runs, every 5 s otherwise, and not at all while the app is in the background */
let pollN = 0;
setInterval(() => { if (document.hidden) return; pollN++; if (S.jobs.some(j => j.status === 'running' || j.status === 'queued') || pollN % 3 === 0) pollJobs(); }, 1500);
document.addEventListener('visibilitychange', () => { if (!document.hidden) pollJobs(); });

/* ================= settings ================= */
async function vSettings() {
  const [s, h] = await Promise.all([api('/api/settings'), api('/api/health')]);
  S.set = s;
  const sg = (key, val, opts) => segc(key, val, opts, 'data-set');
  const sw = (key, label) => `<label class="sw"><span>${label}</span><input type="checkbox" data-set-bool="${key}" ${s[key] !== false ? 'checked' : ''}></label>`;
  const ok = v => v ? '✅' : '⚠️';
  view().innerHTML = `
    <div class="h"><h2>⚙️ ${t('settings')}</h2></div>
    <a class="btn gold big wide" href="#/help" style="margin-bottom:14px">📘 ${t('help')}</a>
    <div class="setgrid">
    <div class="card pad"><div class="field"><label>🌐 ${t('s_lang')}</label>${sg('lang', LANG, [['ar', 'العربية'], ['en', 'English']])}</div>
      <div class="field"${h.web ? ' hidden' : ''}><label>🔗 ${t('s_newlink')}</label>${sg('auto_download', s.auto_download || 'video', [['video', t('as_video')], ['audio', t('as_audio')], ['none', t('as_link')]])}</div></div>
    <div class="card pad"><h3>🎨 ${t('s_look')}</h3>
      <div class="field"><label>${t('s_theme')}</label>${sg('theme', s.theme || 'auto', [['auto', t('auto')], ['light', t('light')], ['dark', t('dark')], ['sepia', t('sepia')]])}</div>
      <div class="field"><label>${t('s_accent')}</label><div class="swatches">${COLORS.map(c => `<button type="button" data-accent="${c}" style="background:${c}" class="${c === s.accent ? 'on' : ''}"></button>`).join('')}</div></div>
      <div class="field"><label>${t('s_zoom')}</label>${segc('zoom', store.get('zoom', 'auto'), [['auto', t('z_auto')], [0.9, '90%'], [1, '100%'], [1.15, '115%'], [1.3, '130%'], [1.5, '150%']], 'data-zoom')}</div>
      <div class="field"><label>${t('s_size')}</label>${sg('font_scale', s.font_scale || 1, [[0.92, t('small')], [1, t('medium')], [1.12, t('large')], [1.25, t('xlarge')]])}</div>
      <div class="field"><label>${t('s_trsize')}</label>${sg('tr_scale', s.tr_scale || 1, [[0.9, t('small')], [1, t('medium')], [1.2, t('large')], [1.4, t('xlarge')]])}</div></div>
    <div class="card pad"><h3>🔤 ${t('s_fonts')}</h3>
      <div class="field"><label>${t('f_ui')}</label>${fontSeg('font_ui', s.font_ui || 'tajawal', 'data-set')}</div>
      <div class="field"><label>${t('f_head')}</label>${fontSeg('font_head', s.font_head || s.font_ui || 'tajawal', 'data-set')}</div>
      <div class="field"><label>${t('f_read')}</label>${fontSeg('font_read', s.font_read || 'amiri', 'data-set')}
        <p class="fprev" style="font-family:${fstack(s.font_read || 'amiri')}">الحمد لله رب العالمين، والصلاة والسلام على نبينا محمد.</p></div></div>
    <div class="card pad"><h3>🤲 ${t('s_dhikr')}</h3><p class="muted small">${t('dhikr_p')}</p>${sg('dhikr', s.dhikr ?? 15, [[0, t('off')], [10, t('m10')], [15, t('m15')]])}${sw('reminders', t('s_rmd'))}</div>
    <div class="card pad"><h3>📝 ${t('s_tr')}</h3>
      <div class="field"><label>${t('s_engine')}</label><select data-set-sel="engine"><option value="groq" ${s.engine === 'groq' ? 'selected' : ''}>${t('engine_groq')}</option>
        ${h.android || h.web ? '' : `<option value="local" ${s.engine === 'local' ? 'selected' : ''}>${t('engine_local')}</option>`}</select></div>
      <div class="field"><label>${t('s_key')} ${s.groq_key_set ? '✅' : ''}</label><input type="password" id="gkey" dir="ltr" placeholder="${s.groq_key_set ? t('key_saved') : 'gsk_…'}">
        <small>${t('key_hint')} <a href="https://console.groq.com/keys" target="_blank">console.groq.com/keys</a></small></div>
      <div class="field"><button class="btn soft big wide" data-act="test-tr">🧪 ${t('test_tr')}</button><div id="testTr" style="margin-top:8px"></div></div>
      <div class="field"><label>${t('s_model')}</label><select data-set-sel="groq_model"><option value="whisper-large-v3" ${s.groq_model === 'whisper-large-v3' ? 'selected' : ''}>${t('model_best')}</option>
        <option value="whisper-large-v3-turbo" ${s.groq_model === 'whisper-large-v3-turbo' ? 'selected' : ''}>${t('model_fast')}</option></select></div>
      <div class="field"><label>${t('s_speech')}</label><select data-set-sel="language">${[['ar', 'العربية'], ['en', 'English'], ['ms', 'Melayu'], ['ur', 'اردو'], ['', 'Auto']].map(([v, n]) => `<option value="${v}" ${s.language === v ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
      <div class="field"><label>${t('s_hint')}</label><input data-set-text="prompt" dir="auto" value="${esc(s.prompt)}" placeholder="${t('hint_ph')}"><small>${t('hint_p')}</small></div></div>
    <div class="card pad"><h3>🖥️ ${t('s_view')}</h3>${sw('show_transcript', t('s_show_tr'))}${sw('follow', t('s_follow'))}
      <label class="sw"><span>${t('s_exact')}</span><input type="checkbox" data-set-bool="reencode_video" ${s.reencode_video ? 'checked' : ''}></label><small class="muted">${t('s_exact_p')}</small></div>
    <div class="card pad"><h3>🔎 ${t('s_search')}</h3><div class="btns nowrap">
      <div class="field grow"><label>${t('pad_before')}</label><input type="number" min="0" max="60" data-set-num="pad_before" value="${s.pad_before}"></div>
      <div class="field grow"><label>${t('pad_after')}</label><input type="number" min="0" max="120" data-set-num="pad_after" value="${s.pad_after}"></div></div></div>
    ${h.web ? '' : `<div class="card pad"><h3>⬇ ${t('s_dl')}</h3><div class="btns nowrap">
      <div class="field grow"><label>${t('s_md')}</label><input type="number" min="1" max="8" data-set-num="max_downloads" value="${s.max_downloads}"></div>
      <div class="field grow"><label>${t('s_mt')}</label><input type="number" min="1" max="6" data-set-num="max_transcribes" value="${s.max_transcribes}"></div></div>
      <div class="field"><label>${t('s_quality')}</label>${sg('video_height', s.video_height, [[9999, '⭐ ' + t('q_orig')], [1080, '1080p'], [720, '720p'], [480, '480p'], [360, '360p']])}</div></div>`}
    ${h.web ? '' : `<div class="card pad"><h3>▶️ ${t('s_yt')}</h3><p>${h.cookies ? '✅ ' + t('ck_on') : 'ℹ️ ' + t('ck_off')}</p>
      <div class="btns"><button class="btn big" data-act="ck-add">🍪 ${t('ck_add')}</button>${h.cookies ? `<button class="btn ghost danger" data-act="ck-del">🗑 ${t('ck_del')}</button>` : ''}
        ${h.hosted ? '' : `<button class="btn" data-act="upd-ytdlp">⬇ ${t('upd_ytdlp')}</button>`}<input type="file" id="ckFile" accept=".txt,text/plain" hidden></div>
      <div class="btns" style="margin-top:10px"><button class="btn pri big wide" data-act="test-yt">🧪 ${t('test_yt')}</button></div><div id="ytRes" style="margin-top:8px"></div>
      <div class="btns" style="margin-top:10px"><button class="btn soft big wide" data-act="test-mirrors">🛰️ ${t('test_mirrors')}</button></div><div id="mirRes" style="margin-top:8px"></div>
      <p class="muted small">${t('ck_p')}</p></div>`}
    ${h.hosted || h.web || IS_LAN ? '' : `<div class="card pad" id="lanCard"><h3>📱 ${t('lan_t')}</h3><p class="muted">${t('lan_p')}</p>
      <label class="sw"><span>${t('lan_sw')}</span><input type="checkbox" id="lanSw"></label><div id="lanBox"></div></div>`}
    ${h.apk ? `<div class="card pad"><h3>🔄 ${t('s_update')}</h3>
      <p class="muted">${t('version')}: <b>${esc(h.version)}</b>${window.MaqatiApp ? ` · ${LANG === 'ar' ? 'التطبيق' : 'App'} <b dir="ltr">${esc(MaqatiApp.appVersion())}</b>` : ''}</p>
      <div class="btns"><button class="btn pri big" data-act="apk-update">🔍 ${t('upd_find')}</button></div>
      <div class="btns" style="margin-top:10px"><button class="btn" data-act="upd-ytdlp">⬇ ${t('upd_ytdlp')}</button><span class="muted small" id="ytdlpMsg">${esc(h.update.msg)}</span></div>
      ${window.MaqatiApp ? `<div class="btns" style="margin-top:10px"><button class="btn ghost" data-act="apk-battery">🔋 ${LANG === 'ar' ? 'السماح بالعمل في الخلفية' : 'Allow background work'}</button></div>` : ''}</div>` : ''}
    ${h.desktop ? `<div class="card pad"><h3>🔄 ${t('s_update')}</h3>
      <p class="muted">${t('version')}: <b>${esc(h.version)}</b></p>
      <div class="btns"><a class="btn pri big" href="https://github.com/beaconcrest8/maqati/releases/latest" target="_blank">⬇ ${t('upd_find')}</a></div>
      <div class="btns" style="margin-top:10px"><button class="btn" data-act="upd-ytdlp">⬇ ${t('upd_ytdlp')}</button><span class="muted small" id="ytdlpMsg">${esc(h.update.msg)}</span></div></div>` : ''}
    ${h.hosted || h.apk || h.web || h.desktop ? '' : `<div class="card pad"><h3>🔄 ${t('s_update')}</h3>
      <p class="muted">${t('version')}: <b>${esc(h.version)}</b></p>
      <div class="btns"><button class="btn pri big" data-act="upd-find">🔍 ${t('upd_find')}</button><button class="btn big" data-act="upd-file">📦 ${t('upd_file')}</button>
        <input type="file" id="updFile" accept=".zip,application/zip" hidden></div><div id="updMsg" style="margin-top:10px"></div>
      <div class="btns" style="margin-top:10px"><button class="btn" data-act="upd-ytdlp">⬇ ${t('upd_ytdlp')}</button><span class="muted small" id="ytdlpMsg">${esc(h.update.msg)}</span></div></div>`}
    ${h.hosted ? `<div class="card pad"><h3>👤 ${LANG === 'ar' ? 'حسابك' : 'Your account'}</h3>
      <p class="muted">${LANG === 'ar' ? 'مسجّل الدخول باسم' : 'Signed in as'}: <b dir="auto">${esc(h.user || '')}</b></p>
      <a class="btn ghost" href="/gw/logout">🚪 ${LANG === 'ar' ? 'تسجيل الخروج' : 'Log out'}</a></div>` : ''}
    <div class="card pad"><h3>🩺 ${t('s_status')}</h3>
      ${h.hosted || h.web ? `<p class="muted">${t('version')}: <b>${esc(h.version)}</b></p>` : ''}
      ${h.web ? `<div>${ok(1)} ${LANG === 'ar' ? 'يعمل داخل المتصفح، وملفاتك محفوظة على هذا الجهاز' : 'Runs inside the browser; your files stay on this device'}</div>` : `<div>${ok(h.ffmpeg)} ffmpeg</div><div>${ok(h.ytdlp)} yt-dlp ${esc(h.ytdlp || '')}</div><div>${ok(h.js)} YouTube helper (${esc(h.js || '—')})</div>`}
      ${h.hosted || h.web ? '' : `<div class="muted small" style="margin-top:8px">${t('files_at')} <span dir="ltr" class="brk">${esc(h.library)}</span></div>`}</div></div>`;
  $('#gkey').onchange = e => saveSet({ groq_key: e.target.value.trim() }).then(() => { e.target.value = ''; vSettings(); });
  if ($('#lanSw')) { lanShow(); $('#lanSw').onchange = async e => { e.target.disabled = true; try { lanShow(await post('/api/lan', { on: e.target.checked })); } catch (err) { toast('✗ ' + err.message); e.target.checked = false; } e.target.disabled = false; }; }
  if ($('#updFile')) $('#updFile').onchange = e => updateFromFile(e.target.files[0]);
  if ($('#ckFile')) $('#ckFile').onchange = async e => { const f = e.target.files[0]; if (!f) return; try { await api('/api/cookies', { method: 'POST', body: f }); toast(t('ck_on')); vSettings(); } catch (err) { toast('✗ ' + err.message); } };
}
const IS_LAN = location.port === '8766';
const IS_WEB = !!window.MAQATI_WEB;        // the iPhone version: the engine runs inside the browser (no links, no Wi-Fi door)
async function lanShow(st) {
  st = st || await api('/api/lan'); const box = $('#lanBox'); if (!box) return;
  $('#lanSw').checked = st.on;
  box.innerHTML = !st.on ? '' : !st.url ? `<p class="warnc">${t('lan_nowifi')}</p>` : `<div class="lanbox">
    <div class="qr">${st.qr || ''}</div><div class="addr">${esc(st.url)}</div>
    <div><small class="muted">${t('lan_code')}</small><div class="code">${esc(st.code)}</div></div></div>
    <ol class="small" style="line-height:2;padding-inline-start:20px">${t('lan_steps').split('|').map(x => `<li>${x}</li>`).join('')}</ol>
    <button class="btn ghost" data-act="lan-new">↻ ${t('lan_new')}</button>`;
}
async function saveSet(obj) {
  await post('/api/settings', obj);
  Object.assign(S.set, obj); if ('groq_key' in obj) delete S.set.groq_key;
  if ('lang' in obj) LANG = obj.lang;
  applyLook(); toast(t('saved'), null, 1200);
}
async function waitRestart(ver) {
  $('#updMsg').innerHTML = `<span class="spin"></span> ${t('upd_wait')}`;
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1500));
    try { const h = await api('/api/health'); if (h.version === ver || i > 8) { toast(t('upd_done', h.version)); setTimeout(() => location.reload(), 800); return; } } catch (e) {}
  }
}
async function updateFromFile(f) {
  if (!f) return;
  $('#updMsg').innerHTML = `<span class="spin"></span> ${t('upd_wait')}`;
  try { const r = await api('/api/update/upload', { method: 'POST', body: f }); waitRestart(r.version); } catch (e) { $('#updMsg').textContent = '✗ ' + e.message; }
}
async function vHelp() {
  let html = '';
  try { html = await (await fetch(`/static/guide/guide-${LANG}.html`, { cache: 'no-cache' })).text(); } catch (e) {}
  view().innerHTML = `<div class="crumbs"><a href="#/settings">${t('settings')}</a> ${SEP()}</div><div class="help">${html || '<p class="muted">…</p>'}</div>`;
}

/* ================= actions: one place for every button ================= */
const markOf = el => S.item && S.item.bookmarks.find(b => b.id === +(el.dataset.b || el.closest('[data-b]').dataset.b));
const clipOf = el => S.project && S.project.clips.find(c => c.id === +el.closest('[data-c]').dataset.c);
const exOf = el => { const id = +el.closest('[data-x]').dataset.x; return (S.item && S.item.excerpts.find(x => x.id === id)) || (S.fc && S.fc.excerpts.find(x => x.id === id)); };
/* go to a moment of the open lesson (reloads the lesson if a part file was playing) */
function seekHere(at, quiet) {
  if (S.item && (!PL.item || PL.item.id !== S.item.id)) { PL.load(S.item, at, true); ui(); }
  else PL.seek(at);
  if (!quiet) toast('▶ ' + fmt(at), null, 1200);
}
async function playAt(itemId, at) {
  if (S.item && S.item.id === itemId) { seekHere(at); return; }
  location.hash = `#/item/${itemId}/${at}`;
}
const ACT = {
  back: () => history.length > 1 ? history.back() : (location.hash = '#/home'),
  add: () => addSheet(),
  'side-toggle': () => document.documentElement.classList.toggle('side'),
  'side-close': () => document.documentElement.classList.remove('side'),
  'lan-new': async () => { lanShow(await post('/api/lan', { on: true, new_code: true })); toast(t('saved')); },
  'import-old': async () => { await post('/api/import-old'); oldBox(); },
  wfold: el => { S.wfold = el.dataset.k; vFolder('all', 'works', true); },
  'rmd-next': el => { const R = window.REMINDERS || []; const i = (store.get('rmi', 0) + 1) % R.length; store.set('rmi', i); store.set('rmt', Date.now());
    const n = document.createElement('div'); n.innerHTML = reminderHTML(); el.replaceWith(n.firstElementChild); const box = $('#rmd'); if (box) box.dataset.i = String(i); },
  'theme-toggle': () => saveSet({ theme: document.documentElement.classList.contains('isdark') ? 'light' : 'dark' }),
  'new-folder': async () => { const id = await customizeFolder(null); if (id) location.hash = '#/lib/f/' + id; },
  'custom-folder': async el => { await loadLib(); const f = S.folders.find(x => x.id === +el.dataset.id); if (await customizeFolder(f)) route(); },
  'del-folder': async el => { if (await ask(t('del_folder_q'), t('delete'), true)) { await del('/api/folders/' + el.dataset.id); location.hash = '#/lib'; } },
  'folder-tr': async el => { const r = await post(`/api/folders/${el.dataset.id}/transcribe-all`); toast(r.queued ? t('queued_n', r.queued) : t('nothing_to_do')); pollJobs(); },
  'export-folder-ex': el => exportSheet('folder_excerpts', el.dataset.id === 'all' ? -1 : el.dataset.id === 'none' ? 0 : el.dataset.id, null, ''),
  // player
  pp: () => PL.toggle(), skip: el => PL.skip(Math.sign(+el.dataset.s) * skipS()),
  'skip-set': el => { store.set('skip', +el.dataset.s); $$('.skn').forEach(x => x.textContent = skipS()); ui(); }, rate: el => { PL.rate(+el.dataset.r); ui(); },
  'audio-only': () => PL.setAudioOnly(!PL.audioOnly), fs: () => { const v = PL.el; if (v && v.requestFullscreen) v.requestFullscreen().catch(() => {}); },
  'go-playing': () => { if (PL.item) { const id = PL.item.parent || PL.item.id; if (typeof id === 'number' || /^\d+$/.test(id)) location.hash = '#/item/' + id; } },
  'pl-close': () => PL.unload(),
  'float-audio': () => PL.setAudioOnly(true),
  'play-at': el => playAt(+el.dataset.item, +el.dataset.t),
  'open-tr': el => { store.set('tr.' + el.dataset.item, el.dataset.k); store.set('itab', 'tr'); location.hash = '#/item/' + el.dataset.item; },
  'export-tr': el => exportSheet('transcript', +el.dataset.tid, null, el.dataset.title),
  'pin-item': async () => { const d = S.item; await patch('/api/items/' + d.id, { pinned: !d.pinned }); d.pinned = d.pinned ? null : Date.now() / 1000; renderMeta(); toast(d.pinned ? '📍 ' + t('pinned') : t('saved')); },
  fgrp: el => { const b = el.closest('.fgbox'); b.classList.toggle('closed'); store.set(el.dataset.k, b.classList.contains('closed')); },
  'lib-view': el => { store.set('libView', el.dataset.v); vLibrary(); },
  'psec-new': async () => { const n = await promptText(t('new_sub'), '', t('sub_ph')); if (!n) return; const p = S.project; if (!p.sections.includes(n)) await patch('/api/projects/' + p.id, { sections: [...p.sections, n] }); vProject(p.id); },
  'psec-ren': async (el, e) => { e && e.preventDefault(); const p = S.project, a = el.dataset.s, n = await promptText(t('rename'), a); if (!n || n === a) return;
    await patch('/api/projects/' + p.id, { sections: p.sections.map(x => x === a ? n : x), rename_section: [a, n] }); vProject(p.id); },
  'psec-del': async (el, e) => { e && e.preventDefault(); const p = S.project, a = el.dataset.s; if (!(await ask(t('del_sub_q', a), t('delete'), true))) return;
    await patch('/api/projects/' + p.id, { sections: p.sections.filter(x => x !== a), rename_section: [a, ''] }); vProject(p.id); },
  'pclip-sec': async el => { const p = S.project, c = p.clips.find(x => x.id === +el.closest('.pclip').dataset.c); const v = await pickSection(p, c.section); if (v === undefined) return; await patch('/api/pclips/' + c.id, { section: v }); vProject(p.id); },
  'clip-open': el => clipSheet(el.dataset.path),
  'clip-proj': async el => { const c = await post('/api/clipfile', { path: el.dataset.path, action: 'info' }); projectSheet([{ item_id: c.item_id, start: c.start, end: c.end, title: c.name }], c.name); },
  'play-file': el => {
    const p = el.dataset.path, id = 'f:' + p;
    if (PL.item && PL.item.id === id) { PL.toggle(); return; }
    const job = el.closest('[data-item]'), parent = +(el.dataset.item || (job && job.dataset.item) || (S.item && S.item.id) || 0) || null;
    PL.load({ id, file: p, media: /\.(mp4|webm|mkv|mov)$/i.test(p) ? 'video' : 'audio', title: p.split('/').pop().replace(/\.[^.]+$/, ''), parent, duration: 0 }, 0, true);
    ui();
  },
  bm: () => bookmarkHere(), mstart: () => markStart(), mend: () => markEnd(),
  // item
  itab: el => showTab(el.dataset.k),
  'tasks-menu': () => sheet(t('tasks'), `<div class="menu"><button class="mi" data-act="jobs-all" data-op="pause" value="x">⏸ ${t('pause_all')}</button>
      <button class="mi" data-act="jobs-all" data-op="resume" value="x">▶ ${t('resume_all')}</button><button class="mi" data-act="jobs-clear" value="x">🧹 ${t('clear_done')}</button></div>`),
  'folder-menu': el => { const fid = el.dataset.id, real = /^\d+$/.test(fid);
    sheet(t('more_opts'), `<div class="menu">
      ${real ? `<button class="mi" data-act="custom-folder" data-id="${fid}" value="x">🎨 ${t('customize')}</button>` : ''}
      <button class="mi" data-act="folder-tr" data-id="${fid}" value="x">📝 ${t('transcribe_all')}</button>
      ${real ? `<button class="mi danger" data-act="del-folder" data-id="${fid}" value="x">🗑 ${t('delete')}</button>` : ''}</div>`); },
  'item-menu': () => sheet(esc(nice(S.item.title)), `<div class="menu">
      <button class="mi" data-act="pin-item" value="x">📍 ${S.item.pinned ? t('unpin') : t('pin')}</button>
      <button class="mi" data-act="item-projects" value="x">💼 ${t('in_projects')}${S.item.projects.length ? ` (${S.item.projects.length})` : ''}</button>
      ${S.item.url ? `<a class="mi" href="${esc(S.item.url)}" target="_blank" rel="noopener">🔗 ${t('source')}</a>` : ''}</div>
      <div class="sectitle">${t('sec_tools')}</div>${toolsHTML()}`),
  'rate-next': () => { const rs = [0.75, 1, 1.25, 1.5, 2], r = rs[(rs.indexOf(PL.rateV) + 1) % rs.length]; PL.rate(r); store.set('rate', r); const tb = $('#pl-tools'); if (tb) tb.innerHTML = playerToolsHTML(); },
  'skip-next': () => { const ss = [5, 10, 15, 30]; store.set('skip', ss[(ss.indexOf(skipS()) + 1) % ss.length]); ui(); const tb = $('#pl-tools'); if (tb) tb.innerHTML = playerToolsHTML(); },
  'fine-toggle': () => { store.set('fineOpen', !store.get('fineOpen', false)); const tb = $('#pl-tools'); if (tb) tb.innerHTML = playerToolsHTML(); },
  'toggle-sec': el => { const s = el.closest('.sec'); s.classList.toggle('closed'); store.set('sec.' + s.dataset.sec, s.classList.contains('closed')); },
  'rename-item': async () => { const n = await promptText(t('rename'), nice(S.item.title)); if (n) { await patch('/api/items/' + S.item.id, { title: n }); refreshItem({ keepTr: true }); } },
  'move-item': async () => {
    await loadLib();
    const r = await sheet('📁 ' + t('move'), `<div class="list">${[[null, '📄', t('unsorted')], ...S.folders.map(f => [f.id, f.icon || '📁', f.name])].map(([id, ic, n]) =>
      `<button class="li" value="${id ?? 'none'}" style="width:100%;text-align:start;${S.item.folder_id === id ? 'border-color:var(--acc);border-width:2px' : ''}"><div class="th" style="width:46px;height:46px">${esc(ic)}</div><div class="tt"><b dir="auto">${esc(n)}</b></div></button>`).join('')}
      <button class="li" value="new" style="width:100%;text-align:start"><div class="th" style="width:46px;height:46px">＋</div><div class="tt"><b>${t('new_folder')}</b></div></button></div>`);
    if (!r || r === 'x') return;
    const fid = r === 'none' ? null : r === 'new' ? await customizeFolder(null) : +r;
    if (r === 'new' && !fid) return;
    await patch('/api/items/' + S.item.id, { move: true, folder_id: fid }); await loadLib(); $('.crumbs').innerHTML = crumbFolder(S.item = { ...S.item, folder_id: fid }); refreshItem({ keepTr: true }); toast(t('saved'));
  },
  'item-projects': () => itemProjectsSheet(S.item),
  'del-item': async () => {
    let files = false;
    const r = await sheet(esc(t('del_item_q', nice(S.item.title))), `<label class="sw"><span>${t('del_files_too')}</span><input type="checkbox" id="delFiles"></label>`,
      `<button class="btn big" value="no">${t('cancel')}</button><button class="btn big danger-fill" value="yes" id="delYes">🗑 ${t('delete')}</button>`,
      d => $('#delYes', d).addEventListener('click', () => { files = $('#delFiles', d).checked; }, true));
    if (r !== 'yes') return;
    const id = S.item.id, fid = S.item.folder_id; if (PL.item && PL.item.id === id) PL.unload();
    await del(`/api/items/${id}?files=${files ? 1 : 0}`); location.hash = '#/lib/f/' + (fid || 'none');
  },
  'item-action': async el => { await post(`/api/items/${S.item.id}/action`, { action: el.dataset.a }); toast(t('in_tasks')); openFiles(); pollJobs(); },
  seek: el => seekHere(+el.dataset.t),
  seg: el => {
    const i = +el.dataset.i;
    if (S.pick) { if (S.pick.a == null) { S.pick.a = i; loadTranscript(); } else finishPick(i); return; }
    seekHere(+el.dataset.t, true);
  },
  'pick-start': () => { if (!S.tr.segs.length) return; S.pick = { a: null }; loadTranscript(); },
  'pick-cancel': () => { S.pick = null; loadTranscript(); },
  // marks
  sel: el => { const id = +el.closest('[data-b]').dataset.b; el.checked ? S.sel.add(id) : S.sel.delete(id); $('#sb-marks').innerHTML = marksHTML(); },
  'sel-all': el => { S.sel = el.checked ? new Set(S.item.bookmarks.map(b => b.id)) : new Set(); $('#sb-marks').innerHTML = marksHTML(); },
  'sel-none': () => { S.sel.clear(); $('#sb-marks').innerHTML = marksHTML(); },
  bulk: async el => {
    const ids = [...S.sel];
    if (el.dataset.a === 'project') return projectSheet(ids.map(id => { const b = S.item.bookmarks.find(x => x.id === id); return { item_id: S.item.id, start: b.start, end: b.end || S.item.duration || b.start + 60, title: b.name }; }));
    const r = await post('/api/bookmarks/action', { ids, action: el.dataset.a }); toast(t('queued_n', r.queued)); pollJobs();
  },
  qmenu: el => {
    const host = el.closest('[data-item]'), itemId = +(el.dataset.item || (host && host.dataset.item) || (S.item && S.item.id));
    const f = el.dataset.f;
    qMenu(el, itemId, f, async q => {
      const qq = f === 'mp3' ? q : q, tag = f === 'mp3' ? (q ? q + ' kbps' : t('q_orig')) : (q >= 9999 ? t('q_orig') : q + 'p');
      if (el.dataset.mode === 'bulk') { const r = await post('/api/bookmarks/action', { ids: [...S.sel], action: f, q: qq }); toast(t('queued_n', r.queued) + ' · ' + tag); pollJobs(); return; }
      if (el.dataset.mode === 'fetch') { await post(`/api/items/${itemId}/action`, { action: 'fetch_video', q: qq }); toast(t('in_tasks') + ' · ' + tag); openFiles(); pollJobs(); return; }
      if (el.dataset.ex) await post(`/api/excerpts/${el.dataset.ex}/clip`, { fmt: f, q: qq });
      else { const bid = +(el.dataset.b || el.closest('[data-b]').dataset.b); await post('/api/bookmarks/action', { ids: [bid], action: f, q: qq }); }
      toast(t('in_tasks') + ' · ' + tag); openFiles(); pollJobs();
    });
  },
  clip: async el => {
    if (el.dataset.ex) { await post(`/api/excerpts/${el.dataset.ex}/clip`, { fmt: el.dataset.f }); }
    else { const bid = +(el.dataset.b || el.closest('[data-b]').dataset.b); await post('/api/bookmarks/action', { ids: [bid], action: el.dataset.f }); }
    el.disabled = true; el.innerHTML = '⏳ …'; toast(t('in_tasks')); openFiles(); pollJobs();
  },
  'job-op': async el => { await post(`/api/jobs/${el.dataset.j}/${el.dataset.op}`); pollJobs(); },
  'job-retry': async el => { await post(`/api/jobs/${el.dataset.j}/retry`); el.disabled = true; pollJobs(); },
  one: async el => {
    const b = markOf(el);
    if (el.dataset.a === 'project') return projectSheet([{ item_id: S.item.id, start: b.start, end: b.end || S.item.duration || b.start + 60, title: b.name }], b.name);
    await post('/api/bookmarks/action', { ids: [b.id], action: el.dataset.a }); toast(t('in_tasks')); pollJobs();
  },
  'tr-pick-b': el => { const tr = S.item.transcripts.find(x => x.bookmark_id === +el.dataset.b); if (tr) { S.tr.key = String(tr.id); store.set('tr.' + S.item.id, S.tr.key); const s = $('[data-sec=tr]'); s.classList.remove('closed'); loadTranscript(); s.scrollIntoView({ behavior: 'smooth' }); } },
  'mark-times': el => markTimes(markOf(el)),
  'sel-mode': () => { S.selMode = !S.selMode; if (!S.selMode) S.sel.clear(); $('#sb-marks').innerHTML = marksHTML(); },
  'mark-more': el => { const b = markOf(el), vid = S.item.media === 'video' || S.item.kind === 'youtube';
    sheet(esc(b.name || t('untitled')), `<div data-b="${b.id}"><div class="menu">
      ${vid ? `<div class="mi plain">${clipBtns(S.item.jobs, j => j.bookmark_id === b.id, '', true, 'video')}</div>` : ''}
      <button class="mi" data-act="one" data-a="project" value="x">💼 ${t('to_project')}</button>
      ${b.done ? '' : `<button class="mi" data-act="mark-times" value="x">✏️ ${t('edit_times')}</button><button class="mi" data-act="mark-note" value="x">💬 ${t('note')}</button>`}
      <button class="mi" data-act="mark-done" value="x">${b.done ? '🔓 ' + t('unlock_s') : '✓ ' + t('done_lock')}</button>
      ${b.done ? '' : `<button class="mi danger" data-act="del-mark" value="x">🗑 ${t('delete')}</button>`}</div></div>`); },
  'part-typed': () => { const id = S.item.id, on = PL.item && PL.item.id === id, x = on ? PL.time() : 0; if (on && PL.playing()) PL.pause(); partSheet(id, x, Math.min(x + 30, S.item.duration || x + 30)); },
  fine: el => { if (!PL.ready()) return; PL.seek(Math.max(0, PL.time() + +el.dataset.d), PL.playing()); },
  'mark-done': el => { S.lockAsk = markOf(el).id; $('#sb-marks').innerHTML = marksHTML(); clearTimeout(S.lockT); S.lockT = setTimeout(() => { if (S.lockAsk) { S.lockAsk = null; const m = $('#sb-marks'); if (m) m.innerHTML = marksHTML(); } }, 5000); },
  'mark-done-no': () => { S.lockAsk = null; $('#sb-marks').innerHTML = marksHTML(); },
  'mark-done-ok': async el => { const b = markOf(el); S.lockAsk = null; await patch('/api/bookmarks/' + b.id, { done: !b.done }); b.done = !b.done; toast(b.done ? '✓ ' + t('done_lock') : '🔓'); refreshItem({ keepTr: true }); },
  'set-end': async el => { const b = markOf(el); if (!PL.ready()) return toast(t('not_ready')); const x = PL.time(); if (x <= b.start) return toast(t('end_after')); await patch('/api/bookmarks/' + b.id, { end: x }); refreshItem({ keepTr: true }); },
  'mark-note': el => { const b = markOf(el); S.noteOpen = S.noteOpen === b.id ? null : b.id; $('#sb-marks').innerHTML = marksHTML(); const ta = $(`[data-b="${b.id}"] textarea`); if (ta) ta.focus(); },
  'del-mark': async el => { const b = markOf(el); if (await ask(t('del_mark_q'), t('delete'), true)) { await del('/api/bookmarks/' + b.id); refreshItem({ keepTr: true }); } },
  // transcript
  'tr-choose': async () => {
    const d = S.item, cur = String(S.tr.key);
    const rows = [['all', t('tr_all'), ''], ...d.transcripts.map(x => [String(x.id), nice(x.title), x.end ? rng(x.start || 0, x.end) : ''])];
    const r = await sheet('📝 ' + t('tr_choose'), `<div class="list">${rows.map(([k, l, sub]) => `<button class="li trli ${cur === k ? 'on' : ''}" value="k:${k}"><div class="tt"><b dir="auto">${esc(l)}</b>${sub ? `<small>${sub}</small>` : ''}</div>${cur === k ? '<span class="okc">✓</span>' : ''}</button>`).join('')}</div>`);
    if (!r || !String(r).startsWith('k:')) return;
    S.tr.key = r.slice(2); store.set('tr.' + d.id, S.tr.key); S.editTr = false; loadTranscript();
  },
  'tr-pick': el => { S.tr.key = el.dataset.k; store.set('tr.' + S.item.id, S.tr.key); S.editTr = false; loadTranscript(); },
  follow: el => saveSet({ follow: el.checked }),
  'tr-edit': () => { if (S.tr.key === 'all') return toast(t('pick_tr')); S.editTr = true; loadTranscript(); },
  'tr-cancel': () => { S.editTr = false; loadTranscript(); },
  'tr-save': async () => {
    const segs = S.tr.segs.map((s, i) => ({ ...s, text: $(`#trbox .seg[data-i="${i}"] textarea`).value }));
    await patch('/api/transcripts/' + S.tr.key, { segments: segs }); S.editTr = false; toast(t('saved')); loadTranscript();
  },
  'tr-copy': () => copy(S.tr.segs.map(s => s.text).join('\n')),
  'tr-rename': async el => { const tr = S.item.transcripts.find(x => x.id === +el.dataset.id); const n = await promptText(t('rename'), tr.title); if (n) { await patch('/api/transcripts/' + tr.id, { title: n }); refreshItem(); } },
  'tr-del': async el => { if (await ask(t('del_tr_q'), t('delete'), true)) { await del('/api/transcripts/' + el.dataset.id); S.tr.key = 'all'; refreshItem(); } },
  export: el => {
    const src = el.dataset.src || 'item';
    if (src === 'project') return exportSheet('project', S.project.id, null, S.project.name);
    if (src === 'transcript') { const tr = S.item.transcripts.find(x => x.id === +el.dataset.tid); return exportSheet('transcript', tr.id, null, tr.title); }
    exportSheet('item', S.item.id, el.dataset.which || 'full', S.item.title);
  },
  // excerpts
  'export-ex': el => { const x = exOf(el); exportSheet('excerpt', x.id, null, x.title); },
  'ex-proj': el => { const x = exOf(el); projectSheet([{ item_id: x.item_id, start: x.start, end: x.end, title: x.title }], x.title); },
  'ex-copy': el => copy(exOf(el).text || ''),
  'ex-more': el => { const x = exOf(el); S.exOpen = S.exOpen === x.id ? null : x.id; const p = $('.extext', el.closest('.excard')); p.classList.toggle('open'); el.textContent = p.classList.contains('open') ? t('less') : t('more'); },
  'ex-rename': async el => { const x = exOf(el); const n = await promptText(t('ex_title'), x.title); if (n != null) { await patch('/api/excerpts/' + x.id, { title: n }); S.item ? refreshItem() : route(); } },
  'ex-del': async el => { const x = exOf(el); if (await ask(t('del_ex_q'), t('delete'), true)) { await del('/api/excerpts/' + x.id); S.item ? refreshItem() : route(); } },
  // notes
  'note-new': () => { S.noteEdit = 'new'; $('#sb-notes').innerHTML = notesHTML(); $('#noteTxt').focus(); },
  'note-edit': el => { S.noteEdit = +el.closest('[data-n]').dataset.n; $('#sb-notes').innerHTML = notesHTML(); $('#noteTxt').focus(); },
  'note-cancel': () => { S.noteEdit = null; $('#sb-notes').innerHTML = notesHTML(); },
  'note-save': async () => {
    const txt = $('#noteTxt').value.trim(); if (!txt) return;
    const cb = $('#noteT'), time = cb.checked && cb.dataset.t !== '' ? +cb.dataset.t : null;
    if (S.noteEdit === 'new') await post(`/api/items/${S.item.id}/notes`, { text: txt, time });
    else await patch('/api/notes/' + S.noteEdit, { text: txt, time });
    S.noteEdit = null; toast(t('saved')); refreshItem({ keepTr: true });
  },
  'note-copy': el => copy(S.item.notes.find(n => n.id === +el.closest('[data-n]').dataset.n).text),
  'note-del': async el => { if (await ask(t('del_note_q'), t('delete'), true)) { await del('/api/notes/' + el.closest('[data-n]').dataset.n); refreshItem({ keepTr: true }); } },
  'open-folder': () => post('/api/open-folder', { path: S.item.dir }),
  // search
  'hit-proj': el => { const h = el.closest('.hit'), x = S.res.results[+h.dataset.r]; projectSheet([hitClip(x, x.hits[+h.dataset.h])]); },
  'hit-mark': async el => { const h = el.closest('.hit'), x = S.res.results[+h.dataset.r], c = hitClip(x, x.hits[+h.dataset.h]); await post(`/api/items/${x.item_id}/bookmarks`, { name: c.title, start: c.start, end: c.end }); toast(t('part_saved')); },
  'hit-ex': async el => { const h = el.closest('.hit'), x = S.res.results[+h.dataset.r], c = hitClip(x, x.hits[+h.dataset.h]); const n = await promptText(t('new_ex'), c.title, t('ex_title_ph')); if (n != null) { await post(`/api/items/${x.item_id}/excerpts`, { start: c.start, end: c.end, title: n }); toast(t('ex_saved')); } },
  'res-all-proj': () => projectSheet(S.res.results.flatMap(x => x.hits.map(h => hitClip(x, h)))),
  // projects
  'new-project': async () => { const n = await promptText(t('new_project'), '', t('project_name')); if (n) { const r = await post('/api/projects', { name: n }); location.hash = '#/project/' + r.id; } },
  'rename-project': async () => { const n = await promptText(t('rename'), S.project.name); if (n) { await patch('/api/projects/' + S.project.id, { name: n }); route(); } },
  'del-project': async () => { if (await ask(t('del_proj_q'), t('delete'), true)) { await del('/api/projects/' + S.project.id); location.hash = '#/projects'; } },
  'proj-zip': async () => { await post(`/api/projects/${S.project.id}/export`, { fmt: 'mp3' }); toast(t('in_tasks')); await vProject(S.project.id); pollJobs(); },
  'proj-lessons': () => projectLessonsSheet(S.project),
  'pclip-move': async el => { await post(`/api/pclips/${clipOf(el).id}/move`, { dir: +el.dataset.d }); vProject(S.project.id); },
  'pclip-del': async el => { await del('/api/pclips/' + clipOf(el).id); vProject(S.project.id); },
  'pclip-times': async el => {
    const c = clipOf(el);
    const r = await sheet(t('edit_times'), `${teHTML('ta', t('start'), c.start, 'start')}${teHTML('tb', t('end'), c.end, 'end')}<small class="muted">${t('time_fmt')}</small>`,
      `<button class="btn big" value="no">${t('cancel')}</button><button class="btn big pri" value="ok">${t('save')}</button>`, d => wireTE(d, mainPlayer(c.item_id)));
    if (r !== 'ok') return;
    const a = parseT($('#ta').value), b = parseT($('#tb').value);
    if (a == null || b == null || a === undefined || b === undefined || b <= a) return toast(t('bad_time'));
    await patch('/api/pclips/' + c.id, { start: a, end: b }); vProject(S.project.id);
  },
  // tasks
  job: async el => { await post(`/api/jobs/${el.closest('[data-j]').dataset.j}/${el.dataset.op}`); pollJobs(); },
  'jobs-all': async el => { await post('/api/jobs-all/' + el.dataset.op); pollJobs(); },
  'jobs-clear': async () => { await post('/api/jobs-clear'); pollJobs(); },
  // settings
  'upd-find': async () => {
    const r = await api('/api/update/check'), box = $('#updMsg');
    if (!r.found) { box.innerHTML = `<p class="muted">${t('upd_none')}</p>`; return; }
    box.innerHTML = `<p>${t('upd_found', esc(r.name), esc(r.version || '?'))}</p><button class="btn pri big" id="updGo">⬇ ${t('upd_install')}</button>`;
    $('#updGo').onclick = async () => { try { const x = await post('/api/update/auto'); waitRestart(x.version); } catch (e) { box.textContent = '✗ ' + e.message; } };
  },
  'upd-file': () => $('#updFile').click(),
  'apk-update': () => { if (window.MaqatiApp) MaqatiApp.checkUpdate(); },
  'apk-battery': () => { if (window.MaqatiApp) MaqatiApp.askBackground(); },
  'ck-add': () => $('#ckFile').click(),
  'test-yt': async el => {
    const box = $('#ytRes'); el.disabled = true; box.innerHTML = '<span class="spin"></span> …';
    try {
      const r = await post('/api/test-youtube');
      box.innerHTML = r.steps.map(s => `<div>${s.ok ? '✅' : '❌'} ${esc(s.text)}</div>`).join('') + (r.tried.length ? `<details class="small muted" style="margin-top:6px"><summary>${LANG === 'ar' ? 'التفاصيل التقنية' : 'Technical details'}</summary>${r.tried.map(x => `<div dir="ltr">${esc(x)}</div>`).join('')}</details>` : '');
    } catch (e) { box.textContent = '❌ ' + e.message; }
    el.disabled = false;
  },
  'test-mirrors': async el => {
    const box = $('#mirRes'); el.disabled = true; box.innerHTML = '<span class="spin"></span> …';
    try {
      const r = await post('/api/test-mirrors'); const ok = r.servers.filter(x => x.ok).length;
      box.innerHTML = `<p><b>${ok ? '✅ ' + t('mir_ok', ok, r.servers.length) : '❌ ' + t('mir_none')}</b></p>` + r.servers.filter(x => x.ok).map(x => `<div class="small" dir="ltr">✅ ${esc(x.server)}</div>`).join('') + `<div class="small muted">❌ ${r.servers.length - ok}</div>`;
    } catch (e) { box.textContent = '❌ ' + e.message; }
    el.disabled = false;
  },
  'ck-del': async () => { await del('/api/cookies'); vSettings(); },
  'test-tr': async () => {
    const box = $('#testTr'); box.innerHTML = '<span class="spin"></span>';
    try { const r = await post('/api/test-transcription'); box.innerHTML = r.steps.map(x => `<div>${x.ok ? '✅' : '❌'} ${esc(x.msg)}</div>`).join(''); }
    catch (e) { box.textContent = '❌ ' + e.message; }
  },
  'upd-ytdlp': async () => { await post('/api/update-downloader'); $('#ytdlpMsg').textContent = '…'; },
};
document.addEventListener('click', e => {
  const card = e.target.closest('.job.tap');
  if (card && !e.target.closest('button, a, input, textarea, audio')) { location.hash = '#/item/' + card.dataset.item; return; }
  const el = e.target.closest('[data-act]'); if (!el || !ACT[el.dataset.act]) return;
  if (el.tagName === 'BUTTON' || el.tagName === 'A') e.preventDefault();
  ACT[el.dataset.act](el, e);
});
document.addEventListener('click', e => { if (e.target.closest('#tabbar a, #tabbar .tadd')) document.documentElement.classList.remove('side'); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') document.documentElement.classList.remove('side'); });
document.addEventListener('click', e => {
  const b = e.target.closest('[data-set] button'); if (b) { const k = b.closest('[data-set]').dataset.set; let v = b.dataset.v; if (/^[\d.]+$/.test(v)) v = +v;
    $$('button', b.parentElement).forEach(x => x.classList.toggle('on', x === b)); saveSet({ [k]: v }).then(() => { if (k === 'lang' || k === 'font_read') vSettings(); }); }
  const z = e.target.closest('[data-zoom] button'); if (z) { $$('button', z.parentElement).forEach(x => x.classList.toggle('on', x === z)); store.set('zoom', z.dataset.v); fitZoom(); }
  const a = e.target.closest('[data-accent]'); if (a) { $$('[data-accent]').forEach(x => x.classList.toggle('on', x === a)); saveSet({ accent: a.dataset.accent }); }
});
function dhikrTick() {
  const m = +(S.set.dhikr ?? 15); if (!m) return;
  let last = store.get('dhikrAt', 0);
  if (!last) { last = Date.now() - m * 60000 + 60000; store.set('dhikrAt', last); }      // first time: one minute after opening
  if (Date.now() - last < m * 60000 || document.hidden) return;
  store.set('dhikrAt', Date.now());
  let el = $('#dhikr'); if (!el) { el = document.createElement('div'); el.id = 'dhikr'; el.dir = 'rtl'; document.body.appendChild(el); }
  el.textContent = 'لا حول ولا قوة إلا بالله'; el.classList.add('on'); setTimeout(() => el.classList.remove('on'), 3000);
}
setInterval(dhikrTick, 15000);
document.addEventListener('change', async e => {
  const el = e.target;
  if (el.dataset.setBool) return saveSet({ [el.dataset.setBool]: el.checked }).then(() => S.item && renderSections());
  if (el.dataset.setSel) return saveSet({ [el.dataset.setSel]: el.value });
  if (el.dataset.setText) return saveSet({ [el.dataset.setText]: el.value.trim() });
  if (el.dataset.setNum) return saveSet({ [el.dataset.setNum]: Math.max(+el.min || 0, +el.value || 0) });
  const k = el.dataset.edit; if (!k) return;
  if (k === 'mark-name') { const b = markOf(el); b.name = el.value; await patch('/api/bookmarks/' + b.id, { name: el.value }); toast(t('saved'), null, 900); }
  if (k === 'mark-note') { const b = markOf(el); b.note = el.value; await patch('/api/bookmarks/' + b.id, { note: el.value }); toast(t('saved'), null, 900); }
  if (k === 'project-desc') { await patch('/api/projects/' + S.project.id, { description: el.value }); toast(t('saved'), null, 900); }
  if (k === 'pclip-title') { await patch('/api/pclips/' + clipOf(el).id, { title: el.value }); toast(t('saved'), null, 900); }
  if (k === 'pclip-note') { await patch('/api/pclips/' + clipOf(el).id, { note: el.value }); toast(t('saved'), null, 900); }
});
document.addEventListener('keydown', e => {
  if (!PL.item || e.ctrlKey || e.metaKey || e.altKey || $('#sheet').open) return;
  if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
  const k = e.key.toLowerCase(), page = S.item && S.item.id === PL.item.id;
  if (k === ' ') { e.preventDefault(); PL.toggle(); }
  else if (k === 'arrowleft') { e.preventDefault(); PL.skip(-skipS()); } else if (k === 'arrowright') { e.preventDefault(); PL.skip(skipS()); }
  else if (k === ',') PL.seek(Math.max(0, PL.time() - 0.1), PL.playing()); else if (k === '.') PL.seek(PL.time() + 0.1, PL.playing());
  else if (page && k === 'b') bookmarkHere(); else if (page && k === 's') markStart(); else if (page && k === 'e') markEnd();
});

/* ================= start ================= */
(async () => {
  await loadSettings();
  await pollJobs();
  await route();
  if (S.set.engine === 'groq' && !S.set.groq_key_set) setTimeout(() => toast(t('key_tip'), { label: t('settings'), fn: () => location.hash = '#/settings' }), 1200);
})();
if ('serviceWorker' in navigator && isSecureContext && !IS_WEB) navigator.serviceWorker.register('/sw.js').catch(() => {});

