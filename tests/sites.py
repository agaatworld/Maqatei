"""Which sites can Maqati read? Asks yt-dlp (the app's downloader) about one public link of each site and prints
a table. Run on GitHub (workflow "Sites"): a datacenter is blocked by some sites more often than a home or phone
connection, so a "no" here is not always a "no" on the phone."""
import json
import subprocess
import sys

SITES = [
    ("YouTube", "https://www.youtube.com/watch?v=jNQXAC9IVRw"),
    ("YouTube Shorts", "https://www.youtube.com/shorts/MRm_lQ6Fmto"),
    ("Facebook", "https://www.facebook.com/facebook/videos/10153231379946729/"),
    ("Facebook (fb.watch)", "https://fb.watch/1wLq7N1lqX/"),
    ("Instagram", "https://www.instagram.com/reel/C2gKRKeLVQH/"),
    ("TikTok", "https://www.tiktok.com/@scout2015/video/6718335390845095173"),
    ("X / Twitter", "https://x.com/SpaceX/status/1732824684683784516"),
    ("Vimeo", "https://vimeo.com/56015672"),
    ("SoundCloud", "https://soundcloud.com/ethmusic/lostin-powers-she-so-heavy"),
    ("Dailymotion", "https://www.dailymotion.com/video/x5kesuj"),
    ("Telegram", "https://t.me/durov/68"),
    ("Archive.org", "https://archive.org/details/Popeye_forPresident"),
]


def probe(url):
    p = subprocess.run([sys.executable, "-m", "yt_dlp", "-J", "--no-playlist", "--no-warnings", url],
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        last = [l for l in p.stderr.strip().splitlines() if l.strip()][-1:] or ["failed"]
        return False, last[0][:160]
    j = json.loads(p.stdout)
    fm = j.get("formats") or [j]
    video = any(f.get("vcodec") not in (None, "none") for f in fm)
    audio = any(f.get("acodec") not in (None, "none") for f in fm)
    return True, f"{(j.get('title') or '')[:50]} · {int(j.get('duration') or 0)}s · {'video' if video else ''}{'+' if video and audio else ''}{'audio' if audio else ''}"


if __name__ == "__main__":
    ok = 0
    for name, url in SITES:
        try:
            good, info = probe(url)
        except Exception as e:
            good, info = False, str(e)[:160]
        ok += good
        print(f"{'OK ' if good else 'NO '} {name:22s} {info}")
    print(f"\n{ok}/{len(SITES)} sites read")
