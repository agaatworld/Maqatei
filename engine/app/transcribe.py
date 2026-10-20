"""Speech-to-text engines. Each returns {"text": str, "segments": [{"start","end","text","words"?}]}.

Accuracy rules (learned the hard way, see CHANGELOG 4.0):
- never send a fixed phrase as the prompt: Whisper treats the prompt as text that came just before,
  so a fixed opening biases every piece. Send the user's glossary and the real end of the previous piece.
- never delete repeated speech: dhikr, "آمين", a verse said twice, a teacher repeating for students are real.
  Only remove known junk phrases and lines Whisper itself marks as guesses over silence."""
import os
import threading
import time

import requests

from .i18n import M
from .media import Cancelled

GROQ_URL = os.environ.get("MAQATI_GROQ_URL", "https://api.groq.com/openai/v1/audio/transcriptions")


def _sleep(sec, cancel, note=None):
    end = time.time() + sec
    while time.time() < end:
        if cancel is not None and cancel.is_set():
            raise Cancelled()
        if note:
            note(int(end - time.time()))
        time.sleep(1)


# phrases Whisper sometimes invents on silence or music (not really spoken)
_JUNK = ("اشتركوا في القناة", "اشترك في القناة", "ترجمة نانسي قنقر", "شكرا للمشاهدة", "شكراً للمشاهدة",
         "لا تنسوا الاشتراك", "Subtitles by", "Thanks for watching")


def clean(segs, words=None):
    """Remove invented lines only: known junk phrases and guesses over silence. Repeats are kept.
    words (optional, from the engine) are attached to the sentence they belong to."""
    out = []
    for x in segs:
        t = x["text"].strip()
        if not t or any(j in t for j in _JUNK):
            continue
        if x.get("no_speech_prob", 0) > 0.6 and x.get("avg_logprob", 0) < -0.8:
            continue
        out.append({"start": float(x["start"]), "end": float(x["end"]), "text": t})
    if words:
        i = 0
        ws = sorted(({"w": (w.get("word") or "").strip(), "s": round(float(w["start"]), 3), "e": round(float(w["end"]), 3)}
                     for w in words if (w.get("word") or "").strip()), key=lambda w: w["s"])
        for k, seg in enumerate(out):
            nxt = out[k + 1]["start"] if k + 1 < len(out) else float("inf")
            mine = []
            while i < len(ws) and ws[i]["s"] < nxt - 0.01:
                if ws[i]["s"] >= seg["start"] - 0.5:
                    mine.append(ws[i])
                i += 1
            if mine:
                seg["words"] = mine
    return out


def prompt_for(s, context=""):
    """The user's glossary (names, books, places) followed by the real last words of the previous piece.
    Whisper only reads about the last 224 tokens of a prompt, so keep it short: context last."""
    glossary = (s.get("prompt") or "").strip()[:300]
    ctx = " ".join((context or "").split())[-220:]
    if ctx and " " in ctx:
        ctx = ctx[ctx.index(" ") + 1:]            # start at a whole word
    return " ".join(x for x in (glossary, ctx) if x).strip()


MIME = {".flac": "audio/flac", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".ogg": "audio/ogg"}


def groq(path, s, cancel=None, note=None, context=""):
    key = (s.get("groq_key") or "").strip()
    if not key:
        raise RuntimeError(M("no_key"))
    data = [("model", s.get("groq_model") or "whisper-large-v3"), ("response_format", "verbose_json"),
            ("temperature", "0"), ("timestamp_granularities[]", "segment"), ("timestamp_granularities[]", "word")]
    if s.get("language"):
        data.append(("language", s["language"]))
    prompt = prompt_for(s, context)
    if prompt:
        data.append(("prompt", prompt))
    mime = MIME.get(path.suffix.lower(), "application/octet-stream")
    fails = 0
    while True:
        if cancel is not None and cancel.is_set():
            raise Cancelled()
        try:
            with open(path, "rb") as f:
                r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"},
                                  files={"file": (path.name, f, mime)}, data=data, timeout=300)
        except requests.RequestException as e:
            fails += 1
            if fails > 6:
                raise RuntimeError(M("no_net") + f" ({e})")
            _sleep(5 * fails, cancel, lambda n: note and note(M("net_wait", n=n)))
            continue
        if r.status_code == 200:
            j = r.json()
            segs = clean(j.get("segments") or [], j.get("words"))
            return {"text": " ".join(x["text"] for x in segs), "segments": segs}
        if r.status_code in (401, 403):
            raise RuntimeError(M("bad_key"))
        if r.status_code == 429:                            # free limit: wait as long as Groq says, then go on
            try:
                wait = min(900, max(3, int(float(r.headers.get("retry-after")))))
            except (TypeError, ValueError):
                wait = 30
            _sleep(wait, cancel, lambda n: note and note(M("limit_wait", n=n)))
            continue
        if r.status_code >= 500:
            fails += 1
            if fails > 6:
                raise RuntimeError(M("refusing"))
            _sleep(10 * fails, cancel, lambda n: note and note(M("busy_wait", n=n)))
            continue
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except Exception:
            msg = r.text
        raise RuntimeError(f"Groq error {r.status_code}: {msg[:250]}")


_model = None
_model_name = None
_model_lock = threading.Lock()


def local(path, s, cancel=None, note=None, on_part=None, context=""):
    global _model, _model_name
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(M("no_offline"))
    name = s.get("local_model") or "large-v3"
    with _model_lock:
        if _model is None or _model_name != name:
            if note:
                note(M("loading_model"))
            _model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
            _model_name = name
        segments, info = _model.transcribe(str(path), language=s.get("language") or None,
                                           initial_prompt=prompt_for(s, context) or None,
                                           beam_size=5, vad_filter=True, word_timestamps=True)
        out = []
        for seg in segments:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            if seg.text.strip():
                x = {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
                if seg.words:
                    x["words"] = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for w in seg.words]
                out.append(x)
            if on_part and info.duration:
                on_part(min(1.0, seg.end / info.duration))
    return {"text": " ".join(x["text"] for x in out), "segments": out}


def engine_ok():
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False
