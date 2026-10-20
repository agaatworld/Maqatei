"""End-to-end test of transcription with the real engine, real ffmpeg and a stand-in Groq:
pieces end inside pauses, audio is lossless FLAC, the prompt carries the glossary and the previous
piece's real words (never a fixed phrase), repeated sentences are kept, word times are stored.
Run:  python3 tests/test_transcribe_pipeline.py"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE, GROQ, APP = 8798, 8797, 8799
GAP, PERIOD = 0.8, 4.8          # the test audio: 4 s of sound, 0.8 s pause, repeated


def call(method, path, body=None, raw=None, port=APP):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"null")


def wait(fn, sec=240):
    end = time.time() + sec
    while time.time() < end:
        try:
            v = fn()
            if v:
                return v
        except Exception:
            pass
        time.sleep(0.5)
    raise AssertionError("timed out")


def main():
    tmp = Path(tempfile.mkdtemp())
    audio = tmp / "درس تجريبي.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    f"aevalsrc=0.5*sin(2*PI*300*t)*lt(mod(t\\,{PERIOD})\\,{PERIOD - GAP}):s=16000:d=780",
                    "-ac", "1", "-b:a", "64k", str(audio)], check=True)
    env = {**os.environ, "MAQATI_DATA": str(tmp / "data"), "MAQATI_LIBRARY": str(tmp / "lib"), "MAQATI_OPEN": "0",
           "MAQATI_PORT": str(APP), "PYTHONPATH": str(ROOT / "engine" / "vendor"),   # the bundled requests, as on the phone
           "MAQATI_GROQ_URL": f"http://127.0.0.1:{GROQ}/openai/v1/audio/transcriptions"}
    procs = [subprocess.Popen([sys.executable, str(ROOT / "tests" / "mock_groq.py"), str(GROQ)]),
             subprocess.Popen([sys.executable, "-m", "app.main"], cwd=ROOT / "engine", env=env,
                              stdout=subprocess.DEVNULL, stderr=open(tmp / "engine.log", "w"))]
    try:
        def up():
            if procs[1].poll() is not None:
                raise SystemExit("engine stopped:\n" + (tmp / "engine.log").read_text()[-3000:])
            return call("GET", "/api/health")
        wait(up)
        call("POST", "/api/settings", {"groq_key": "test", "language": "ar", "prompt": "ابن تيمية، صحيح البخاري"})
        from urllib.parse import quote
        iid = call("POST", "/api/upload?name=" + quote(audio.name), raw=audio.read_bytes())["ids"][0]
        call("POST", f"/api/items/{iid}/action", {"action": "transcribe"})
        job = wait(lambda: next((j for j in call("GET", "/api/jobs") if j["kind"] == "transcribe"
                                 and j["status"] in ("done", "error")), None))
        assert job["status"] == "done", (job, (tmp / "engine.log").read_text()[-2000:])
        item = call("GET", f"/api/items/{iid}")
        tid = item["transcripts"][0]["id"]
        t = call("GET", f"/api/transcripts/{tid}")
        segs = t["segments"] if isinstance(t["segments"], list) else json.loads(t["segments"])
        log = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{GROQ}/log").read())

        # 1. lossless audio, word timestamps asked for
        assert all(x["type"] == "audio/flac" for x in log), log
        assert all(x["gran"] == ["segment", "word"] for x in log), log
        # 2. pieces end inside a pause (never mid-sound), about 5 minutes long
        cuts, acc = [], 0.0
        for x in log[:-1]:
            acc += x["dur"]
            cuts.append(acc)
        assert len(log) == 3, [x["dur"] for x in log]
        for c in cuts:
            phase = c % PERIOD
            assert PERIOD - GAP - 0.1 <= phase <= PERIOD + 0.1 or phase < 0.1, ("cut inside sound", c, phase)
        # 3. prompts: glossary + previous piece's real words, never the old fixed opening
        assert log[0]["prompt"] == "ابن تيمية، صحيح البخاري", log[0]["prompt"]
        for k in (1, 2):
            assert log[k]["prompt"].startswith("ابن تيمية"), log[k]["prompt"]
            assert f"جملة {k}-" in log[k]["prompt"], log[k]["prompt"]
        assert not any("أما بعد" in x["prompt"] for x in log)
        # 4. nothing lost, nothing doubled: every piece's sentences arrive, in time order
        starts = [s["start"] for s in segs]
        assert starts == sorted(starts) and len(set(starts)) == len(starts)
        expected = sum(len([1 for _ in range(int((x["dur"] - 0.5) // 4.8) + 1)]) for x in log)
        assert abs(len(segs) - expected) <= 3, (len(segs), expected)
        # 5. the same sentence said again is kept (old code dropped the 3rd repeat and loops)
        assert sum("الحمد لله" in s["text"] for s in segs) == len(segs)
        # 6. word times stored, on the lesson's timeline
        assert all(s.get("words") for s in segs)
        assert all(s["start"] - 0.6 <= s["words"][0]["s"] <= s["end"] for s in segs)
        print(f"OK: {len(log)} pieces cut at pauses {[round(c, 2) for c in cuts]}, {len(segs)} sentences")
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
