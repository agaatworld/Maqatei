"""Lesson map: reads a lesson's transcript and divides it into detailed chapters, each with a title and the exact
sentence where it starts: every topic, every story, and every question someone asked (the question itself is the
title of the answer that follows it). Uses Groq's free chat models with the same key as transcription.

Long lessons are read in pieces (the free plan allows only a few thousand words a minute); finished pieces are kept,
so a paused or interrupted map continues where it stopped. Each piece is told how the previous one ended, so a topic
that runs across two pieces is not split."""
import json
import os
import re

import requests

from . import db
from .export import item_segments
from .i18n import M
from .media import Cancelled
from .transcribe import _sleep

CHAT_URL = os.environ.get("MAQATI_GROQ_CHAT_URL", "https://api.groq.com/openai/v1/chat/completions")
MODELS_URL = os.environ.get("MAQATI_GROQ_MODELS_URL", "https://api.groq.com/openai/v1/models")
# the best free text models first; the list Groq gives decides what is really available today
PREFER = ("openai/gpt-oss-120b", "llama-3.3-70b-versatile", "moonshotai/kimi-k2-instruct", "qwen/qwen3-32b",
          "openai/gpt-oss-20b", "meta-llama/llama-4-maverick-17b-128e-instruct", "llama-3.1-8b-instant")
PIECE = 6000          # characters of transcript per request (about 6 minutes of speech): smaller reads finer

ASK = """هذا {part}تفريغ درس أو محاضرة. كل سطر يبدأ برقمه بين [ ].
قسّمه إلى أبواب مفصّلة ودقيقة: بابًا جديدًا عند كل تغيّر في الموضوع، وكل قصة، وكل سؤال.
أعد JSON فقط، بلا أي كلام قبله أو بعده، بهذا الشكل:
{{"chapters":[{{"l":12,"kind":"topic","title":"..."}}]}}
- l: رقم السطر الذي يبدأ فيه الباب بالضبط كما هو مكتوب بين [ ] (أول جملة من الموضوع الجديد، لا قبلها ولا بعدها).
- kind: "q" إذا بدأ الباب بسؤال من سائل أو طالب (ومنه أن يقرأ الشيخ السؤال: «يقول السائل…») ثم جاء جوابه، و"story" للقصة، و"topic" لغير ذلك.
- title: لسؤال (q) اكتب السؤال نفسه مختصرًا واضحًا بصيغة السؤال. لغيره عنوان من 2 إلى 8 كلمات يصف ما في الباب بدقة (مثل: «قصة الرجل الذي قتل مئة نفس»، «شروط لا إله إلا الله»).
- لا تجعل الأسئلة التي يطرحها الشيخ في شرحه أبوابًا من نوع q.
- الأبواب متتابعة لا تتداخل، وطول الباب عادة من دقيقة إلى بضع دقائق حسب الكلام، فلا تدمج موضوعين مختلفين في باب.
- اكتب بلغة الدرس نفسها، ولا تضف شيئًا ليس في النص.{prev}

النص:
{text}"""
PREV = "\n- آخر باب في الجزء السابق كان: «{t}». إن كان أول هذا الجزء تكملةً له فلا تبدأ بابًا عند السطر الأول."


def _headers(s):
    key = (s.get("groq_key") or "").strip()
    if not key:
        raise RuntimeError(M("no_key"))
    return {"Authorization": f"Bearer {key}"}


def pick_model(s):
    """The first preferred chat model this key can use (Groq retires models; ask what exists today)."""
    if s.get("map_model"):
        return s["map_model"]
    have = []
    try:
        r = requests.get(MODELS_URL, headers=_headers(s), timeout=30)
        if r.status_code in (401, 403):
            raise RuntimeError(M("bad_key"))
        if r.status_code == 200:
            have = [m.get("id", "") for m in (r.json().get("data") or [])]
    except (requests.RequestException, ValueError):
        pass
    for m in PREFER:
        if m in have:
            return m
    text = [m for m in have if not re.search(r"whisper|guard|tts|orpheus|prompt|distil", m)]
    return text[0] if text else PREFER[0]


def _json(text):
    """The JSON object inside a model's answer (models sometimes wrap it in ``` or add a word)."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < a:
        raise ValueError("no JSON")
    return json.loads(text[a:b + 1])


class TooBig(Exception):
    pass


def chat(s, model, prompt, cancel=None, note=None):
    body = {"model": model, "temperature": 0.2, "max_tokens": 4000,
            "messages": [{"role": "system", "content": "أنت مساعد دقيق يفهرس الدروس والمحاضرات العربية. تجيب بـ JSON فقط."},
                         {"role": "user", "content": prompt}]}
    if model.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"
    elif model.startswith("qwen/"):
        body["reasoning_format"] = "hidden"
    fails = 0
    while True:
        if cancel is not None and cancel.is_set():
            raise Cancelled()
        try:
            r = requests.post(CHAT_URL, headers=_headers(s), json=body, timeout=180)
        except requests.RequestException as e:
            fails += 1
            if fails > 6:
                raise RuntimeError(M("no_net") + f" ({e})")
            _sleep(5 * fails, cancel, lambda n: note and note(M("net_wait", n=n)))
            continue
        if r.status_code == 200:
            try:
                return _json(r.json()["choices"][0]["message"]["content"])
            except (ValueError, KeyError, IndexError):
                fails += 1
                if fails > 3:
                    raise RuntimeError(M("map_bad_answer"))
                body["temperature"] = 0.0
                continue
        if r.status_code in (401, 403):
            raise RuntimeError(M("bad_key"))
        if r.status_code == 413 or (r.status_code == 400 and re.search(r"too large|context.length|maximum context", r.text, re.I)):
            raise TooBig()            # this piece is more than the model or the free plan takes at once
        if r.status_code == 429:
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


def pieces(segs, size):
    """[[line number, ...]] groups of sentences; the model sees each sentence as "[number] text"."""
    out, cur, n = [], [], 0
    for i, x in enumerate(segs):
        ln = len(x["text"]) + 8
        if cur and n + ln > size:
            out.append(cur)
            cur, n = [], 0
        cur.append(i)
        n += ln
    if cur:
        out.append(cur)
    return out


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        m = re.search(r"\d+(?:\.\d+)?", str(v or ""))
        return float(m.group()) if m else None


def tidy(parts, segs):
    chapters = []
    for p in parts:
        for c in p.get("chapters") or []:
            ln, title = _num(c.get("l")), str(c.get("title") or "").strip()
            if ln is None or not title:
                continue
            ln = max(0, min(len(segs) - 1, int(ln)))
            kind = c.get("kind") if c.get("kind") in ("q", "story", "topic") else "topic"
            if chapters and ln <= chapters[-1]["l"]:
                if ln == chapters[-1]["l"] and kind == "q" and chapters[-1]["kind"] != "q":
                    chapters[-1].update(kind=kind, title=title[:200])      # the question wins as the title
                continue
            chapters.append({"l": ln, "t": segs[ln]["start"], "kind": kind, "title": title[:200]})
    if chapters:
        chapters[0]["t"] = min(chapters[0]["t"], segs[0]["start"])
    else:
        chapters = [{"l": 0, "t": segs[0]["start"], "kind": "topic", "title": "—"}]
    for i, c in enumerate(chapters):
        c["end"] = chapters[i + 1]["t"] if i + 1 < len(chapters) else segs[-1]["end"]
        del c["l"]
    return {"chapters": chapters}


def make_map(item, workdir, cancel=None, progress=None):
    s = db.get_settings()
    segs = item_segments(item["id"])
    if not segs:
        raise RuntimeError(M("map_need_tr"))
    note = (lambda m: progress(None, m)) if progress else None
    model = pick_model(s)
    size = PIECE
    while True:
        chunks = pieces(segs, size)
        state = workdir / f"map-{size}.json"
        done = json.loads(state.read_text(encoding="utf-8")) if state.exists() else []
        try:
            for i in range(len(done), len(chunks)):
                if progress:
                    progress(i / len(chunks), M("map_reading", d=i + 1, n=len(chunks)))
                last = next((c.get("title") for p in reversed(done) for c in reversed(p.get("chapters") or []) if c.get("title")), None)
                text = "\n".join(f"[{k}] {segs[k]['text'].strip()}" for k in chunks[i])
                part = "" if len(chunks) == 1 else f"الجزء {i + 1} من {len(chunks)} من "
                done.append(chat(s, model, ASK.format(part=part, prev=PREV.format(t=last) if last else "", text=text),
                                 cancel, note))
                state.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
            break
        except TooBig:
            if size <= 1500:
                raise RuntimeError(M("map_too_big"))
            size //= 2
    m = tidy(done, segs)
    m["model"] = model
    db.run("INSERT OR REPLACE INTO maps (item_id, data, created) VALUES (?,?,?)",
           (item["id"], json.dumps(m, ensure_ascii=False), db.now()))
    return m


def get_map(item_id):
    r = db.one("SELECT data, created FROM maps WHERE item_id=?", (item_id,))
    if not r:
        return None
    try:
        return dict(json.loads(r["data"]), created=r["created"])
    except ValueError:
        return None
