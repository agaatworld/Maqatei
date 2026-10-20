#!/usr/bin/env bash
# Runs on the CI emulator: installs the app, opens it like a person would, and checks that the
# engine really works on Android (Python, ffmpeg, yt-dlp with SSL, the web page) with no Termux.
set -euo pipefail
PKG=com.turathpro.maqati
APK=$(ls app/build/outputs/apk/debug/*x86_64*.apk | head -1)
OUT=smoke-out
mkdir -p $OUT
adb install -r -g "$APK"
# answer the first-run questions the way the owner would (allow files, notifications, background)
adb shell appops set $PKG MANAGE_EXTERNAL_STORAGE allow
adb shell pm grant $PKG android.permission.POST_NOTIFICATIONS || true
adb shell dumpsys deviceidle whitelist +$PKG
adb shell am start -n $PKG/com.maqati.app.MainActivity
adb forward tcp:8775 tcp:8775

log() { adb shell run-as $PKG cat files/data/engine.log > $OUT/engine.log 2>/dev/null || true; }
trap 'log; adb exec-out screencap -p > $OUT/last.png || true; adb logcat -d > $OUT/logcat.txt || true' EXIT

echo "waiting for the engine…"
for i in $(seq 1 240); do
  if curl -sf http://127.0.0.1:8775/api/health -o $OUT/health.json; then break; fi
  sleep 1
done
cat $OUT/health.json; echo
python3 - $OUT/health.json <<'PY'
import json, sys
h = json.load(open(sys.argv[1]))
assert h["apk"] is True, h
assert h["ffmpeg"], h
assert h["ytdlp"], h
assert h["js"] == "quickjs", h
assert "/Maqati" in h["library"], h
print("health OK:", h["version"], "yt-dlp", h["ytdlp"])
PY

# a real file through ffmpeg (upload -> probe) and an MP3 part cut
ffmpeg -v error -f lavfi -i "sine=frequency=440:duration=20" -ac 1 -b:a 64k $OUT/tone.mp3
ID=$(curl -sf -X POST --data-binary @$OUT/tone.mp3 "http://127.0.0.1:8775/api/upload?name=%D8%AF%D8%B1%D8%B3.mp3" | python3 -c "import json,sys;print(json.load(sys.stdin)['ids'][0])")
curl -sf http://127.0.0.1:8775/api/items/$ID -o $OUT/item.json
python3 -c "import json;i=json.load(open('$OUT/item.json'));d=i.get('duration') or i.get('item',{}).get('duration');assert d and abs(d-20)<0.5,i;print('ffmpeg probe OK',d)"

# yt-dlp through Python with SSL: read a link
curl -sf -X POST -H 'Content-Type: application/json' -d '{"text":"https://upload.wikimedia.org/wikipedia/commons/c/c8/Example.ogg","mode":"none"}' http://127.0.0.1:8775/api/links
for i in $(seq 1 120); do
  curl -sf http://127.0.0.1:8775/api/jobs -o $OUT/jobs.json
  if python3 -c "import json,sys;j=[x for x in json.load(open('$OUT/jobs.json')) if x['kind']=='info'];sys.exit(0 if j and j[0]['status'] in ('done','error') else 1)"; then break; fi
  sleep 1
done
python3 -c "import json;j=[x for x in json.load(open('$OUT/jobs.json')) if x['kind']=='info'][0];assert j['status']=='done',j;print('yt-dlp link OK')"

# the page itself shows (screenshot kept as an artifact)
sleep 3
adb exec-out screencap -p > $OUT/app.png
curl -sf http://127.0.0.1:8775/ | grep -q "app.js" && echo "page OK"

# open from an iPhone: the Wi-Fi door answers with the code page, and keeps the library locked
curl -sf -X POST -H 'Content-Type: application/json' -d '{"on":true}' http://127.0.0.1:8775/api/lan > $OUT/lan.json
adb forward tcp:8766 tcp:8766
curl -sf http://127.0.0.1:8766/ | grep -q "lan-login" && echo "Wi-Fi code page OK"
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8766/api/state)" = "401" && echo "Wi-Fi locked without code OK"
curl -sf -X POST -H 'Content-Type: application/json' -d '{"on":false}' http://127.0.0.1:8775/api/lan > /dev/null
echo "SMOKE TEST PASSED"
