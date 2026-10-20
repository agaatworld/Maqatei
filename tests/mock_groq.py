"""A stand-in for the Groq transcription API, for tests. It answers like Groq (verbose_json with
segments and words) and records what the app sent: prompt, file type, audio length."""
import json
import subprocess
import sys
import tempfile
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = []


def duration(data):
    with tempfile.NamedTemporaryFile(suffix=".bin") as f:
        f.write(data)
        f.flush()
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f.name],
                             capture_output=True, text=True).stdout
    return float(out.strip() or 0)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps(LOG).encode() if self.path == "/log" else b'{"data":[]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers["Content-Length"])
        raw = self.rfile.read(n)
        msg = BytesParser(policy=default).parsebytes(
            b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + raw)
        fields, file_type, audio = {}, None, b""
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if part.get_filename():
                file_type, audio = part.get_content_type(), part.get_payload(decode=True)
            else:
                fields.setdefault(name, []).append(part.get_payload(decode=True).decode("utf-8"))
        d = duration(audio)
        LOG.append({"prompt": (fields.get("prompt") or [""])[0], "type": file_type, "dur": d,
                    "gran": fields.get("timestamp_granularities[]")})
        segs, words, t, k = [], [], 0.0, len(LOG)
        while t < d - 0.5:
            e = min(d, t + 4.8)
            text = f"جملة {k}-{int(t)} الحمد لله"
            segs.append({"start": t, "end": e, "text": " " + text, "no_speech_prob": 0.01, "avg_logprob": -0.2,
                         "compression_ratio": 3.0})
            for j, w in enumerate(text.split()):
                words.append({"word": w, "start": t + j, "end": t + j + 0.9})
            t = e
        body = json.dumps({"text": " ".join(s["text"] for s in segs), "segments": segs, "words": words}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
