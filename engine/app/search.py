"""Search inside every transcript. Arabic-aware: ignores tashkeel and alef/yaa/taa-marbuta spelling differences."""
import re

from . import db
from .export import item_segments

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ئ": "ي", "ؤ": "و", "ة": "ه"})


def norm(s):
    s = _TASHKEEL.sub("", s or "").translate(_MAP).lower()
    return re.sub(r"[^\w\s]", " ", s)


def terms(q):
    """'صلاة الفجر, قيام الليل' → two phrases (any of them matches)."""
    return [norm(t).split() for t in re.split(r"[,،|\n]+", q or "") if norm(t).strip()]


def search(q, folder=None, limit=400):
    phrases = terms(q)
    if not phrases:
        return {"results": [], "untranscribed": 0}
    items = db.q("SELECT * FROM items" + (" WHERE folder_id=?" if folder not in (None, "", "all") else ""),
                 (() if folder in (None, "", "all") else (int(folder),)))
    results, untranscribed = [], 0
    for it in items:
        segs = item_segments(it["id"])
        if not segs:
            untranscribed += 1
            continue
        normed = [norm(s["text"]) for s in segs]
        hits = []
        for i in range(len(segs)):
            # look at this segment joined with the next one, so phrases split across lines are found
            here = " " + normed[i] + " "
            nxt = " " + (normed[i + 1] if i + 1 < len(segs) else "") + " "
            window = here + nxt
            for ph in phrases:
                phrase = " ".join(ph)
                in_here = phrase in here or (len(ph) > 1 and all(w in here for w in ph))
                in_next = phrase in nxt or (len(ph) > 1 and all(w in nxt for w in ph))
                # found in this sentence, or spread across this one and the next
                spans = not in_next and (phrase in window or (len(ph) > 1 and all(w in window for w in ph)))
                if in_here or spans:
                    if hits and hits[-1]["last"] >= i - 1 and segs[i]["end"] - hits[-1]["start"] < 150:
                        # the topic continues in the next sentence: make that hit (and its clip) longer
                        hits[-1]["last"] = i
                        hits[-1]["end"] = max(hits[-1]["end"], segs[i]["end"])
                        break
                    ctx_a, ctx_b = max(0, i - 1), min(len(segs), i + 3)
                    hits.append({"i": i, "last": i, "start": segs[i]["start"], "end": segs[i]["end"],
                                 "before": " ".join(s["text"] for s in segs[ctx_a:i]),
                                 "text": segs[i]["text"],
                                 "after": " ".join(s["text"] for s in segs[i + 1:ctx_b]),
                                 "match": " ".join(ph)})
                    break
        if hits:
            results.append({"item_id": it["id"], "title": it["title"], "folder_id": it["folder_id"],
                            "kind": it["kind"], "media": it["media"],
                            "thumb": it["thumb"], "hits": [{k: v for k, v in h.items() if k not in ("i", "last")} for h in hits]})
        if sum(len(r["hits"]) for r in results) > limit:
            break
    results.sort(key=lambda r: -len(r["hits"]))
    return {"results": results, "untranscribed": untranscribed, "words": [" ".join(p) for p in phrases]}
