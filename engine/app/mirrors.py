"""Free backup sources for YouTube, used only when YouTube blocks this phone with
"Sign in to confirm you're not a bot". Public servers come and go, so the list is refreshed
from the live public directories (cached 6 hours) and every server is asked at the same time."""
import json
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

PIPED = ["https://pipedapi.kavin.rocks", "https://pipedapi.leptons.xyz", "https://pipedapi.nosebs.ru",
         "https://pipedapi-libre.kavin.rocks", "https://piped-api.privacy.com.de", "https://pipedapi.adminforge.de",
         "https://api.piped.yt", "https://pipedapi.drgns.space", "https://pipedapi.owo.si", "https://pipedapi.ducks.party",
         "https://piped-api.codespace.cz", "https://pipedapi.reallyaweso.me", "https://api.piped.private.coffee",
         "https://pipedapi.darkness.services", "https://pipedapi.orangenet.cc"]
INVIDIOUS = ["https://inv.nadeko.net", "https://invidious.nerdvpn.de", "https://yewtu.be", "https://inv.tux.pizza",
             "https://invidious.privacyredirect.com", "https://iv.melmac.space", "https://invidious.f5.si",
             "https://yt.artemislena.eu", "https://invidious.materialio.us"]
COBALT = ["https://cobalt-api.kwiatekmiki.com", "https://cobalt.api.timelessnesses.me", "https://api.co.rooot.gay",
          "https://cobalt-api.meowing.de", "https://api.cobalt.tools"]
UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36"}
_cache = {"t": 0, "lists": None}


def _extra():
    """Servers the user added in data/mirrors.txt (one address per line)."""
    try:
        from . import db
        f = db.DATA / "mirrors.txt"
        return [l.strip().rstrip("/") for l in f.read_text(encoding="utf-8").splitlines() if l.strip().startswith("http")]
    except Exception:
        return []


def servers():
    """[(kind, base)] from the live public lists + the built-in ones (refreshed every 6 hours)."""
    if _cache["lists"] and time.time() - _cache["t"] < 6 * 3600:
        return _cache["lists"]
    piped, inv, cob = list(PIPED), list(INVIDIOUS), list(COBALT)

    def get(u):
        try:
            return requests.get(u, headers=UA, timeout=(4, 8))
        except Exception:
            return None
    with ThreadPoolExecutor(4) as ex:
        r1, r2, r3, r4 = ex.map(get, [
            "https://piped-instances.kavin.rocks/",
            "https://raw.githubusercontent.com/TeamPiped/documentation/main/content/docs/public-instances/index.md",
            "https://api.invidious.io/instances.json?sort_by=health",
            "https://instances.cobalt.best/api/instances.json"])
    try:
        piped += [x["api_url"].rstrip("/") for x in r1.json() if x.get("api_url")]
    except Exception:
        pass
    try:
        piped += re.findall(r"\|\s*(https://[^\s|]+)\s*\|", r2.text)
    except Exception:
        pass
    try:
        inv = [x[1]["uri"].rstrip("/") for x in r3.json()
               if x[1].get("api") and x[1].get("type") == "https"] + inv
    except Exception:
        pass
    try:
        for x in r4.json():
            if x.get("api") and "youtube" in json.dumps(x.get("services") or {}).lower():
                cob.append("https://" + x["api"].split("//")[-1].rstrip("/"))
    except Exception:
        pass
    uniq = lambda xs: list(dict.fromkeys(xs))[:25]
    out = ([("piped", b) for b in uniq(piped)] + [("invidious", b) for b in uniq(inv)] +
           [("cobalt", b) for b in uniq(cob)])
    for b in _extra():
        kind = "invidious" if "inv" in b else ("cobalt" if "cobalt" in b else "piped")
        out.insert(0, (kind, b))
    _cache.update(t=time.time(), lists=out)
    return out


def _cobalt(vid, bases=None):
    """cobalt returns one ready file (video with sound) that ffmpeg can read directly."""
    for base in bases or COBALT:
        try:
            r = requests.post(base.rstrip("/") + "/", headers={**UA, "Accept": "application/json",
                              "Content-Type": "application/json"},
                              json={"url": f"https://www.youtube.com/watch?v={vid}", "videoQuality": "720",
                                    "youtubeVideoCodec": "h264"}, timeout=(4, 15))
            j = r.json()
            if j.get("status") not in ("tunnel", "redirect", "stream") or not j.get("url"):
                continue
            u = j["url"]
            title = re.sub(r"\s*\(\d+p.*$|\.\w+$", "", j.get("filename") or "") or None
            return {"title": title, "duration": 0, "thumb": "",
                    "audio": [{"url": u, "abr": 128, "mime": "video/mp4"}],
                    "video": [{"url": u, "h": 720, "mime": "video/mp4", "only": False}]}
        except Exception:
            continue
    return None


def _piped(vid, bases=None):
    for base in bases or PIPED:
        try:
            r = requests.get(f"{base}/streams/{vid}", headers=UA, timeout=(4, 10))
            if r.status_code != 200:
                continue
            j = r.json()
            if not j.get("audioStreams"):
                continue
            aud = [{"url": a["url"], "abr": (a.get("bitrate") or 0) / 1000, "mime": a.get("mimeType", "")} for a in j["audioStreams"]]
            vids = [{"url": v["url"], "h": int(str(v.get("quality", "0")).rstrip("p").split("p")[0] or 0),
                     "mime": v.get("mimeType", ""), "only": v.get("videoOnly", True)} for v in j.get("videoStreams") or []]
            return {"title": j.get("title"), "duration": j.get("duration") or 0, "thumb": j.get("thumbnailUrl") or "",
                    "audio": aud, "video": vids}
        except Exception:
            continue
    return None


def _invidious(vid, bases=None):
    for base in bases or INVIDIOUS:
        try:
            r = requests.get(f"{base}/api/v1/videos/{vid}?local=true", headers=UA, timeout=(4, 10))
            if r.status_code != 200:
                continue
            j = r.json()
            fix = lambda u: u if u.startswith("http") else base + u
            aud, vids = [], []
            for f in j.get("adaptiveFormats") or []:
                t = f.get("type", "")
                if t.startswith("audio"):
                    aud.append({"url": fix(f["url"]), "abr": int(f.get("bitrate") or 0) / 1000, "mime": t})
                elif t.startswith("video"):
                    vids.append({"url": fix(f["url"]), "h": int(str(f.get("resolution", "0p")).rstrip("p") or 0), "mime": t, "only": True})
            for f in j.get("formatStreams") or []:
                vids.append({"url": fix(f["url"]), "h": int(str(f.get("resolution", "0p")).rstrip("p") or 0),
                             "mime": f.get("type", ""), "only": False})
            if not aud and not vids:
                continue
            thumbs = j.get("videoThumbnails") or [{}]
            return {"title": j.get("title"), "duration": j.get("lengthSeconds") or 0, "thumb": thumbs[0].get("url", ""),
                    "audio": aud, "video": vids}
        except Exception:
            continue
    return None


def _one(kind, base, vid):
    return {"piped": _piped, "invidious": _invidious, "cobalt": _cobalt}[kind](vid, [base])


def check_all(vid="jNQXAC9IVRw"):
    """Ask every server at the same time; return [(server, ok, title)] as they answer."""
    jobs = servers()
    out = []
    pool = ThreadPoolExecutor(min(64, len(jobs)))
    futs = {pool.submit(_single, k, b, vid): b for k, b in jobs}
    try:
        for f in as_completed(futs, timeout=20):
            try:
                m = f.result()
            except Exception:
                m = None
            out.append((futs[f], bool(m), (m or {}).get("title")))
    except Exception:
        pass
    pool.shutdown(wait=False, cancel_futures=True)
    done = {x[0] for x in out}
    out += [(b, False, None) for b in futs.values() if b not in done]
    return out


def _single(kind, base, vid):
    if kind == "cobalt":
        return _cobalt(vid, [base])
    if kind == "piped":
        r = requests.get(f"{base}/streams/{vid}", headers=UA, timeout=(4, 10))
        if r.status_code == 200 and r.json().get("audioStreams"):
            return {"title": r.json().get("title")}
    else:
        r = requests.get(f"{base}/api/v1/videos/{vid}?local=true", headers=UA, timeout=(4, 10))
        if r.status_code == 200 and (r.json().get("adaptiveFormats") or r.json().get("formatStreams")):
            return {"title": r.json().get("title")}
    return None


def lookup(vid):
    """All servers are asked at once; the first good answer wins (about 10 seconds at most).
    Piped/Invidious are preferred (real duration, seekable); cobalt is used if nothing else answers."""
    jobs = servers()
    pool = ThreadPoolExecutor(min(64, len(jobs)))
    best = []
    try:
        futs = [pool.submit(_one, k, b, vid) for k, b in jobs]
        for f in as_completed(futs, timeout=20):
            try:
                m = f.result()
            except Exception:
                m = None
            if m and m["duration"]:
                return m
            if m and not best:
                best.append(m)
    except Exception:
        pass
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return best[0] if best else None


def inputs(info, want, height=720):
    """Same shape as media.stream_urls: [(url, headers, kind)]"""
    mp4 = lambda x: "mp4" in x["mime"] or "m4a" in x["mime"]
    aud = sorted(info["audio"], key=lambda a: (not mp4(a), -a["abr"]))
    if want == "speech":
        small = sorted([a for a in info["audio"] if a["abr"] >= 40], key=lambda a: a["abr"])
        pick = (small or aud)[:1]
        return [(p["url"], "", "a") for p in pick]
    if want == "audio":
        return [(aud[0]["url"], "", "a")] if aud else []
    h = int(height or 720)
    muxed = sorted([v for v in info["video"] if not v["only"] and v["h"] <= h], key=lambda v: (not mp4(v), -v["h"]))
    if muxed:
        return [(muxed[0]["url"], "", "av")]
    vo = sorted([v for v in info["video"] if v["only"] and v["h"] <= h], key=lambda v: (not mp4(v), -v["h"]))
    if vo and aud:
        return [(vo[0]["url"], "", "v"), (aud[0]["url"], "", "a")]
    # nothing this small: the nearest larger picture. A video request never gets sound only.
    up = sorted([v for v in info["video"] if not v["only"] or aud], key=lambda v: (v["h"], v["only"], not mp4(v)))
    if up:
        v = up[0]
        return [(v["url"], "", "av")] if not v["only"] else [(v["url"], "", "v"), (aud[0]["url"], "", "a")]
    return []
