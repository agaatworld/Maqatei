"""Turn transcripts into a nicely laid-out book: printable HTML (→ PDF), Word (.docx) or plain text."""
import html
import io
import json
import re
import zipfile
from datetime import date

from . import db, media
from .i18n import lang

T = {  # book labels
    "contents": ("Contents", "المحتويات"),
    "notes": ("Notes & benefits", "الفوائد والملاحظات"),
    "source": ("Source", "المصدر"),
    "from_to": ("{a} – {b}", "{a} – {b}"),
    "empty": ("(no transcript for this part yet)", "(لا يوجد تفريغ لهذا الجزء بعد)"),
    "print_hint": ("To save as PDF: choose “Save as PDF” as the printer, then Save.",
                   "للحفظ PDF: اختر «حفظ بتنسيق PDF» كطابعة ثم اضغط حفظ."),
    "print_btn": ("Save as PDF / Print", "حفظ PDF / طباعة"),
    "made_with": ("Made with Maqati", "صُنع بتطبيق مقاطع"),
}


def L(k, **kw):
    en, ar = T[k]
    return (ar if lang() == "ar" else en).format(**kw)


def clock(t):
    t = int(t or 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------- gathering text ----------
def item_segments(item_id, a=0.0, b=None):
    """All known transcript segments of an item inside [a, b], without duplicates.
    Full transcripts are preferred; clip transcripts fill the gaps."""
    rows = db.q("SELECT * FROM transcripts WHERE item_id=? ORDER BY (bookmark_id IS NOT NULL), id", (item_id,))
    kept = []
    for r in rows:
        for s in json.loads(r["segments"] or "[]"):
            if s["end"] <= a or (b is not None and s["start"] >= b):
                continue
            ln = max(0.01, s["end"] - s["start"])
            if any(min(k["end"], s["end"]) - max(k["start"], s["start"]) > 0.5 * ln for k in kept):
                continue
            kept.append(s)
    kept.sort(key=lambda s: s["start"])
    return kept


def paragraphs(segs, mode="auto", breaks=()):
    """Group segments into readable paragraphs: [{'t': start, 'text': ...}].
    `breaks` are times where a titled part starts: a paragraph never runs across them."""
    brk = sorted(breaks)
    if mode == "lines":
        return [{"t": s["start"], "e": s["end"], "text": s["text"].strip()} for s in segs if s["text"].strip()]
    out, cur, last_end = [], None, None
    for s in segs:
        txt = s["text"].strip()
        if not txt:
            continue
        gap = (s["start"] - last_end) if last_end is not None else 0
        crosses = cur is not None and any(cur["t"] < b <= s["start"] + 0.5 for b in brk)
        if cur is None or crosses or gap > 1.6 or len(cur["text"]) > 650 or (
                len(cur["text"]) > 260 and re.search(r"[.!?؟۔…]$", cur["text"])):
            cur = {"t": s["start"], "e": s["end"], "text": txt}
            out.append(cur)
        else:
            cur["text"] += " " + txt
            cur["e"] = s["end"]
        last_end = s["end"]
    return out


# the six fonts: key -> (css family, name Word uses)
FONTS = {"plex": ("Plex", "IBM Plex Sans Arabic"), "tajawal": ("Tajawal", "Tajawal"), "almarai": ("Almarai", "Almarai"),
         "amiri": ("Amiri", "Amiri"), "naskh": ("Naskh", "Noto Naskh Arabic"), "scheherazade": ("Scheherazade", "Scheherazade New")}


def css_font(k):
    return f'{FONTS.get(k, FONTS["amiri"])[0]},"Traditional Arabic",serif'


def chunks(s, mode):
    """What a section prints, in order: ('h', title) headings and ('p', time, text) paragraphs.
    When you set your own paragraphs (title + start + end) those are used exactly."""
    if s.get("paras") is not None:
        for p in s["paras"]:
            txt = " ".join(x["text"].strip() for x in s["segs"]
                           if p["start"] - 0.05 <= (x["start"] + x["end"]) / 2 < p["end"] + 0.05 and x["text"].strip())
            if p.get("title"):
                yield ("h", p["title"])
            if txt:
                yield ("p", p["start"], txt)
        return
    heads = list(s.get("heads") or [])
    for p in paragraphs(s["segs"], mode, [h["t"] for h in heads]):
        while heads and heads[0]["t"] <= p["t"] + 0.5:
            yield ("h", heads.pop(0)["title"])
        yield ("p", p["t"], p["text"])


def own_paras(scope):
    row = db.one("SELECT data FROM paras WHERE scope=?", (scope,))
    return json.loads(row["data"]) if row else None


def project_clips(pid):
    """A project's clips in reading order: loose clips first, then each sub-folder in its own order."""
    import json as _json
    p = db.one("SELECT sections FROM projects WHERE id=?", (pid,)) or {}
    try:
        order = _json.loads(p.get("sections") or "[]")
    except ValueError:
        order = []
    clips = db.q("SELECT c.*, i.title AS item_title FROM project_clips c LEFT JOIN items i ON i.id=c.item_id "
                 "WHERE project_id=? ORDER BY pos, id", (pid,))
    rank = lambda c: -1 if not c.get("section") else (order.index(c["section"]) if c["section"] in order else len(order))
    return sorted(clips, key=rank)


def build(src, sid, which="full", tid=None):
    """Return a book model {title, subtitle, sections:[{heading, sub, segs, note}], notes:[...]}"""
    if src in ("item", "transcript", "excerpt", "project") and sid <= 0:
        raise ValueError("id")
    if src == "project":
        p = db.one("SELECT * FROM projects WHERE id=?", (sid,))
        clips = project_clips(sid)
        secs = [{"heading": c["title"] or c["item_title"] or "",
                 "sub": (f"📁 {c['section']} · " if c.get("section") else "") + f"{c['item_title'] or ''} · "
                        + L("from_to", a=clock(c["start"]), b=clock(c["end"])),
                 "segs": item_segments(c["item_id"], c["start"], c["end"]), "note": c["note"] or ""} for c in clips]
        return {"title": p["name"], "subtitle": p["description"] or "", "sections": secs, "notes": []}

    if src == "excerpt":
        x = db.one("SELECT * FROM excerpts WHERE id=?", (sid,))
        item = db.one("SELECT * FROM items WHERE id=?", (x["item_id"],))
        return {"title": x["title"] or item["title"], "subtitle": item["title"], "notes": [],
                "sections": [{"heading": "", "sub": L("from_to", a=clock(x["start"]), b=clock(x["end"])),
                              "segs": item_segments(x["item_id"], x["start"], x["end"]), "note": x["note"] or ""}]}

    if src == "folder_excerpts":
        where = "" if sid == -1 else ("WHERE i.folder_id IS NULL " if sid == 0 else "WHERE i.folder_id=? ")
        rows = db.q("SELECT x.*, i.title AS item_title FROM excerpts x JOIN items i ON i.id=x.item_id "
                    + where + "ORDER BY i.id, x.start", () if sid in (0, -1) else (sid,))
        f = db.one("SELECT * FROM folders WHERE id=?", (sid,)) if sid > 0 else None
        return {"title": f["name"] if f else ("المقتطفات" if lang() == "ar" else "Excerpts"), "subtitle": "", "notes": [],
                "sections": [{"heading": x["title"] or clock(x["start"]),
                              "sub": f"{x['item_title']} · " + L("from_to", a=clock(x["start"]), b=clock(x["end"])),
                              "segs": item_segments(x["item_id"], x["start"], x["end"]), "note": x["note"] or ""} for x in rows]}

    if src == "transcript":
        t = db.one("SELECT * FROM transcripts WHERE id=?", (sid,))
        item = db.one("SELECT * FROM items WHERE id=?", (t["item_id"],))
        notes = db.q("SELECT * FROM notes WHERE item_id=? ORDER BY COALESCE(time, 1e12), id", (item["id"],))
        return {"title": t["title"], "subtitle": item["title"], "notes": notes,
                "sections": [{"heading": "", "sub": "", "segs": json.loads(t["segments"] or "[]"), "note": "",
                              "paras": own_paras(f"tr:{sid}")}]}

    item = db.one("SELECT * FROM items WHERE id=?", (sid,))
    notes = db.q("SELECT * FROM notes WHERE item_id=? ORDER BY COALESCE(time, 1e12), id", (sid,))
    secs = []
    heads = [{"t": x["start"], "title": x["title"]} for x in
             db.q("SELECT * FROM excerpts WHERE item_id=? AND title!='' ORDER BY start", (sid,))]
    if which in ("full", "both"):
        secs.append({"heading": "" if which == "full" else item["title"], "sub": "",
                     "segs": item_segments(sid), "note": "", "heads": heads,
                     "paras": own_paras(f"item:{sid}") if which == "full" else None})
    if which == "excerpts":
        for x in db.q("SELECT * FROM excerpts WHERE item_id=? ORDER BY start", (sid,)):
            secs.append({"heading": x["title"] or clock(x["start"]),
                         "sub": L("from_to", a=clock(x["start"]), b=clock(x["end"])),
                         "segs": item_segments(sid, x["start"], x["end"]), "note": x["note"] or ""})
    if which in ("clips", "both"):
        for b in db.q("SELECT * FROM bookmarks WHERE item_id=? ORDER BY start", (sid,)):
            end = b["end"] or item["duration"] or None
            secs.append({"heading": b["name"] or clock(b["start"]),
                         "sub": L("from_to", a=clock(b["start"]), b=clock(end) if end else "…"),
                         "segs": item_segments(sid, b["start"], end), "note": b["note"] or ""})
    return {"title": item["title"], "subtitle": "", "sections": secs, "notes": notes}


def ts_span(t):
    return f'<span class="ts">{clock(t)}</span>'


# ---------- HTML (for reading and for PDF via the browser's "Save as PDF") ----------
SIZES = {"s": 15, "m": 17.5, "l": 20.5, "xl": 24, "xxl": 28}


def render_html(book, o, auto_print=False):
    rtl = lang() == "ar"
    e = html.escape
    fs = SIZES.get(o.get("size"), 17.5)
    accent = o.get("accent") or "#0d6e5f"
    title = o.get("title") or book["title"]
    subtitle = o.get("subtitle") if o.get("subtitle") is not None else book["subtitle"]
    author = o.get("author") or ""
    secs = book["sections"]
    parts = []
    if o.get("cover", True):
        parts.append(f"""<section class="cover"><div class="orn">❁</div><h1>{e(title)}</h1>
          {f'<p class="sub">{e(subtitle)}</p>' if subtitle else ''}{f'<p class="author">{e(author)}</p>' if author else ''}
          <div class="orn small">✦ ✦ ✦</div><p class="date">{date.today().isoformat()}</p></section>""")
    else:
        parts.append(f'<header class="plain"><h1>{e(title)}</h1>{f"<p class=sub>{e(subtitle)}</p>" if subtitle else ""}</header>')
    named = [s for s in secs if s["heading"]]
    if o.get("toc", True) and len(named) > 1:
        parts.append(f'<section class="toc"><h2>{L("contents")}</h2><ol>' +
                     "".join(f'<li><a href="#s{i}">{e(s["heading"])}</a><span>{e(s["sub"])}</span></li>'
                             for i, s in enumerate(secs) if s["heading"]) + "</ol></section>")
    for i, s in enumerate(secs):
        out = []
        for c in chunks(s, o.get("mode", "auto")):
            out.append(f'<h3 class="part">{e(c[1])}</h3>' if c[0] == "h"
                       else "<p>" + (ts_span(c[1]) if o.get("ts") else "") + e(c[2]) + "</p>")
        body = "".join(out) or f'<p class="empty">{L("empty")}</p>'
        head = f'<h2 id="s{i}">{e(s["heading"])}</h2>' if s["heading"] else ""
        sub = f'<p class="secsub">{e(s["sub"])}</p>' if s["sub"] else ""
        note = f'<blockquote>{e(s["note"])}</blockquote>' if s.get("note") else ""
        parts.append(f'<section class="chap">{head}{sub}{note}<div class="txt">{body}</div></section>')
    if o.get("notes", True) and book["notes"]:
        parts.append(f'<section class="chap notes"><h2>{L("notes")}</h2><ul>' + "".join(
            "<li>" + (ts_span(n["time"]) if n["time"] is not None else "") + e(n["text"]).replace("\n", "<br>") + "</li>"
            for n in book["notes"]) + "</ul></section>")
    printer = f"""<div class="bar noprint"><button onclick="mqPrint()">🖨 {L('print_btn')}</button><small>{L('print_hint')}</small></div>
      <script>function mqPrint(){{if(window.MaqatiApp)MaqatiApp.print(document.title);else print()}}</script>
      {'<script>addEventListener("load",()=>setTimeout(()=>mqPrint(),600))</script>' if auto_print else ''}"""
    return f"""<!doctype html><html lang="{'ar' if rtl else 'en'}" dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)}</title>
<link rel="stylesheet" href="/static/fonts.css">
<style>
@page{{size:A4;margin:22mm 20mm 20mm}}
:root{{--acc:{accent};--f:{css_font(o.get("font"))};--hf:{css_font(o.get("hfont") or o.get("font"))}}}
h1,h2,h3{{font-family:var(--hf);font-weight:700}}
*{{box-sizing:border-box}}
body{{margin:0;background:#efebe2;color:#1d2321;font-family:var(--f);font-size:{fs}px;line-height:2.05}}
.page{{max-width:800px;margin:24px auto;background:#fffdf8;padding:56px 64px;box-shadow:0 4px 30px rgba(0,0,0,.08);border-radius:4px}}
.cover{{min-height:88vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;page-break-after:always;border:1.5px solid var(--acc);outline:6px double color-mix(in srgb,var(--acc) 35%,transparent);outline-offset:6px;padding:40px;margin-bottom:40px}}
.cover h1{{font-size:2.4em;line-height:1.5;margin:.3em 0;color:var(--acc)}}
.cover .sub{{font-size:1.25em;margin:0;color:#4a524f}}.cover .author{{font-size:1.1em;margin:.8em 0 0}}
.cover .date{{font-family:Plex,sans-serif;font-size:.7em;color:#8a918e;margin-top:2em}}
.orn{{font-size:2.2em;color:var(--acc)}}.orn.small{{font-size:1em;letter-spacing:.6em;margin-top:1.4em}}
header.plain{{text-align:center;border-bottom:2px solid var(--acc);margin-bottom:1.5em}}header.plain h1{{color:var(--acc);margin:.2em 0}}
.toc{{page-break-after:always}}.toc h2,.chap h2{{color:var(--acc);font-size:1.55em;margin:1.2em 0 .1em;line-height:1.5}}
.toc ol{{padding-inline-start:1.4em}}.toc li{{margin:.25em 0}}.toc a{{color:inherit;text-decoration:none}}
.toc li span{{font-family:Plex,sans-serif;font-size:.62em;color:#8a918e;margin-inline-start:.8em}}
.chap{{margin-bottom:2.2em}}.chap+.chap h2{{page-break-before:auto}}
.secsub{{font-family:Plex,sans-serif;font-size:.68em;color:#7b837f;margin:0 0 1em;border-bottom:1px solid #e4dfd4;padding-bottom:.6em}}
.txt p{{margin:0 0 1.05em;text-align:justify;text-indent:1.2em}}
h3.part{{color:var(--acc);font-size:1.18em;margin:1.3em 0 .4em;padding-inline-start:.6em;border-inline-start:4px solid var(--acc);line-height:1.6}}
.ts{{font-family:Plex,sans-serif;font-size:.6em;color:var(--acc);background:color-mix(in srgb,var(--acc) 10%,transparent);border-radius:4px;padding:1px 6px;margin-inline-end:.6em;text-indent:0;display:inline-block;line-height:1.6;vertical-align:.25em}}
blockquote{{margin:0 0 1em;padding:.4em 1em;border-inline-start:3px solid #a97f2e;background:#f6efdd;border-radius:4px}}
.notes ul{{padding-inline-start:1.2em}}.notes li{{margin-bottom:.7em}}
.empty{{color:#9aa2a0;font-style:italic}}
.bar{{position:sticky;top:0;z-index:5;display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap;background:#1d2321;color:#fff;padding:10px;font-family:Plex,sans-serif}}
.bar button{{font:inherit;font-size:16px;background:var(--acc);color:#fff;border:0;border-radius:10px;padding:10px 18px}}
.bar small{{opacity:.8}}
.foot{{text-align:center;font-family:Plex,sans-serif;font-size:.6em;color:#a2a9a6;margin-top:3em}}
@media (max-width:700px){{.page{{padding:28px 20px;margin:0}}.cover{{min-height:70vh}}}}
@media print{{body{{background:#fff}}.page{{box-shadow:none;margin:0;padding:0;max-width:none;background:transparent}}.noprint{{display:none}}
  .cover{{min-height:235mm;margin:4mm 6mm 0}}.txt p{{orphans:3;widows:3}}h2{{page-break-after:avoid}}}}
</style></head><body>{printer}<main class="page">{''.join(parts)}<p class="foot">{L('made_with')}</p></main></body></html>"""


# ---------- plain text ----------
def render_txt(book, o):
    title = o.get("title") or book["title"]
    out = [title, "=" * min(60, max(10, len(title)))]
    sub = o.get("subtitle") if o.get("subtitle") is not None else book["subtitle"]
    if sub:
        out.append(sub)
    if o.get("author"):
        out.append(o["author"])
    out.append("")
    for s in book["sections"]:
        if s["heading"]:
            out += ["", s["heading"], "-" * min(50, max(6, len(s["heading"])))]
        if s["sub"]:
            out.append(s["sub"])
        if s.get("note"):
            out.append("« " + s["note"] + " »")
        out.append("")
        for c in chunks(s, o.get("mode", "auto")):
            if c[0] == "h":
                out += ["", "■ " + c[1], ""]
            else:
                out += [(f"[{clock(c[1])}] " if o.get("ts") else "") + c[2], ""]
    if o.get("notes", True) and book["notes"]:
        out += ["", L("notes"), "-" * 20]
        out += [(f"[{clock(n['time'])}] " if n["time"] is not None else "") + n["text"] for n in book["notes"]]
    return "\n".join(out).strip() + "\n"


# ---------- Word (.docx), built by hand so no extra software is needed ----------
def _x(s):
    return html.escape(s or "", quote=False)


def render_docx(book, o):
    rtl = lang() == "ar"
    acc = (o.get("accent") or "#0d6e5f").lstrip("#")
    half = int(SIZES.get(o.get("size"), 17.5) * 1.3)      # docx sizes are half-points
    font = FONTS.get(o.get("font"), FONTS["amiri"])[1]
    hfont = FONTS.get(o.get("hfont") or o.get("font"), FONTS["amiri"])[1]
    bidi = "<w:bidi/>" if rtl else ""
    rtlr = "<w:rtl/>" if rtl else ""

    def run(text, size=None, color=None, bold=False):
        f = hfont if bold else font
        pr = f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/>' + ("<w:b/><w:bCs/>" if bold else "") + \
             (f'<w:color w:val="{color}"/>' if color else "") + \
             f'<w:sz w:val="{size or half}"/><w:szCs w:val="{size or half}"/>{rtlr}'
        return f'<w:r><w:rPr>{pr}</w:rPr><w:t xml:space="preserve">{_x(text)}</w:t></w:r>'

    def para(runs, align=None, after=240, before=0, indent=True, brk=False):
        jc = f'<w:jc w:val="{align}"/>' if align else '<w:jc w:val="both"/>'
        ind = '<w:ind w:firstLine="340"/>' if indent else ""
        pb = "<w:pageBreakBefore/>" if brk else ""
        return (f'<w:p><w:pPr>{pb}{bidi}{jc}<w:spacing w:before="{before}" w:after="{after}" w:line="400" w:lineRule="auto"/>'
                f'{ind}</w:pPr>{runs}</w:p>')

    title = o.get("title") or book["title"]
    sub = o.get("subtitle") if o.get("subtitle") is not None else book["subtitle"]
    body = []
    if o.get("cover", True):
        body.append(para("", after=2400, indent=False))
        body.append(para(run("❁", half * 2, acc), "center", indent=False))
        body.append(para(run(title, half * 2 + 8, acc, True), "center", after=200, indent=False))
        if sub:
            body.append(para(run(sub, half + 6, "4A524F"), "center", indent=False))
        if o.get("author"):
            body.append(para(run(o["author"], half + 2), "center", indent=False))
        body.append(para(run(date.today().isoformat(), half - 8, "8A918E"), "center", before=600, indent=False))
    else:
        body.append(para(run(title, half * 2, acc, True), "center", indent=False))
        if sub:
            body.append(para(run(sub, half + 4, "4A524F"), "center", indent=False))
    first = True
    for s in book["sections"]:
        if s["heading"]:
            body.append(para(run(s["heading"], half + 12, acc, True), "left" if not rtl else "right",
                             before=360, after=80, indent=False, brk=o.get("cover", True) and first))
            first = False
        elif o.get("cover", True) and first:
            body.append(para("", indent=False, brk=True, after=0))
            first = False
        if s["sub"]:
            body.append(para(run(s["sub"], half - 8, "7B837F"), "left" if not rtl else "right", after=200, indent=False))
        if s.get("note"):
            body.append(para(run(s["note"], half, "A97F2E"), after=200, indent=False))
        ps = list(chunks(s, o.get("mode", "auto")))
        for c in ps:
            if c[0] == "h":
                body.append(para(run(c[1], half + 6, acc, True), "left" if not rtl else "right",
                                 before=240, after=100, indent=False))
                continue
            rs = (run(clock(c[1]) + "  ", half - 10, acc) if o.get("ts") else "") + run(c[2])
            body.append(para(rs))
        if not ps:
            body.append(para(run(L("empty"), half - 4, "9AA2A0"), indent=False))
    if o.get("notes", True) and book["notes"]:
        body.append(para(run(L("notes"), half + 12, acc, True), before=480, after=120, indent=False))
        for n in book["notes"]:
            rs = (run(clock(n["time"]) + "  ", half - 10, acc) if n["time"] is not None else "") + run("• " + n["text"])
            body.append(para(rs, indent=False, after=160))
    sect = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1300" w:right="1200" w:bottom="1200" '
            'w:left="1200" w:header="600" w:footer="600" w:gutter="0"/>' + ("<w:bidi/>" if rtl else "") + '</w:sectPr>')
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
           + "".join(body) + sect + "</w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   '</Relationships>')
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


def filename(book, o, ext):
    return media.safe_name(o.get("title") or book["title"]) + "." + ext
