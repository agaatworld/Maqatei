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

# a video link with separate picture and sound (like YouTube): yt-dlp must join them with the phone's ffmpeg,
# then a video part is cut from it, and another straight from the site (no download)
DASH=https://storage.googleapis.com/shaka-demo-assets/angel-one/dash.mpd
VID=$(curl -sf -X POST -H 'Content-Type: application/json' -d "{\"text\":\"$DASH\",\"mode\":\"video\",\"q\":360}" http://127.0.0.1:8775/api/links | python3 -c "import json,sys;print(json.load(sys.stdin)['ids'][0])")
for i in $(seq 1 300); do
  curl -sf http://127.0.0.1:8775/api/jobs -o $OUT/jobs-video.json
  if python3 -c "import json,sys;j=[x for x in json.load(open('$OUT/jobs-video.json')) if x['item_id']==$VID];sys.exit(0 if j and all(x['status'] in ('done','error') for x in j) and (any(x['kind']=='fetch' for x in j) or any(x['status']=='error' for x in j)) else 1)"; then break; fi
  sleep 1
done
python3 -c "
import json
j=[x for x in json.load(open('$OUT/jobs-video.json')) if x['item_id']==$VID]
for x in j: print('  ', x['kind'], x['status'], (x.get('result') or x.get('message') or '')[:300])
f=[x for x in j if x['kind']=='fetch']
assert f and f[0]['status']=='done', 'VIDEO DOWNLOAD FAILED'
print('video download (picture + sound joined) OK')"
curl -sf http://127.0.0.1:8775/api/items/$VID -o $OUT/item-video.json
python3 -c "import json;i=json.load(open('$OUT/item-video.json'));assert i['media']=='video' and i['file'],i;print('video item OK',i['file'],i['duration'])"
BV=$(curl -sf -X POST -H 'Content-Type: application/json' -d '{"name":"v","start":5,"end":15}' http://127.0.0.1:8775/api/items/$VID/bookmarks | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
curl -sf -X POST -H 'Content-Type: application/json' -d "{\"ids\":[$BV],\"action\":\"video\",\"q\":240}" http://127.0.0.1:8775/api/bookmarks/action > /dev/null
curl -sf -X POST -H 'Content-Type: application/json' -d "{\"ids\":[$BV],\"action\":\"video\"}" http://127.0.0.1:8775/api/bookmarks/action > /dev/null
for i in $(seq 1 240); do
  curl -sf http://127.0.0.1:8775/api/jobs -o $OUT/jobs-clip.json
  if python3 -c "import json,sys;j=[x for x in json.load(open('$OUT/jobs-clip.json')) if x['kind']=='clip' and x['bookmark_id']==$BV];sys.exit(0 if len(j)==2 and all(x['status'] in ('done','error') for x in j) else 1)"; then break; fi
  sleep 1
done
python3 -c "
import json
j=[x for x in json.load(open('$OUT/jobs-clip.json')) if x['kind']=='clip' and x['bookmark_id']==$BV]
for x in j: print('  ', x['title'], x['status'], (x.get('result') or x.get('message') or '')[:300])
assert len(j)==2 and all(x['status']=='done' for x in j), 'VIDEO PART FAILED'
print('video parts (original and 240p) OK')"
# a link kept as a link: the part is read straight from the site
LID=$(curl -sf -X POST -H 'Content-Type: application/json' -d "{\"text\":\"$DASH\",\"mode\":\"none\"}" http://127.0.0.1:8775/api/links | python3 -c "import json,sys;print(json.load(sys.stdin)['ids'][0])")
for i in $(seq 1 120); do
  curl -sf http://127.0.0.1:8775/api/items/$LID -o $OUT/item-link.json
  if python3 -c "import json,sys;i=json.load(open('$OUT/item-link.json'));sys.exit(0 if i['duration'] else 1)"; then break; fi
  sleep 1
done
BL=$(curl -sf -X POST -H 'Content-Type: application/json' -d '{"name":"l","start":3,"end":9}' http://127.0.0.1:8775/api/items/$LID/bookmarks | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
curl -sf -X POST -H 'Content-Type: application/json' -d "{\"ids\":[$BL],\"action\":\"video\",\"q\":360}" http://127.0.0.1:8775/api/bookmarks/action > /dev/null
for i in $(seq 1 240); do
  curl -sf http://127.0.0.1:8775/api/jobs -o $OUT/jobs-link.json
  if python3 -c "import json,sys;j=[x for x in json.load(open('$OUT/jobs-link.json')) if x['kind']=='clip' and x['bookmark_id']==$BL];sys.exit(0 if j and j[0]['status'] in ('done','error') else 1)"; then break; fi
  sleep 1
done
python3 -c "
import json
j=[x for x in json.load(open('$OUT/jobs-link.json')) if x['kind']=='clip' and x['bookmark_id']==$BL]
print('  ', j[0]['status'], (j[0].get('result') or j[0].get('message') or '')[:300])
assert j[0]['status']=='done', 'VIDEO PART FROM LINK FAILED'
print('video part straight from a link OK')"
log

# removing music on the phone: the app's own code runs the real model (downloaded on first use) on the 20 s tone
python3 -c "import json;h=json.load(open('$OUT/health.json'));assert h.get('music'), 'MUSIC REMOVAL NOT AVAILABLE';print('music removal available')"
T0=$(date +%s)
MJ=$(curl -sf -X POST -H 'Content-Type: application/json' -d "{\"item_id\":$ID}" http://127.0.0.1:8775/api/demusic | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
for i in $(seq 1 900); do
  curl -sf http://127.0.0.1:8775/api/jobs -o $OUT/jobs-music.json
  if python3 -c "import json,sys;j=[x for x in json.load(open('$OUT/jobs-music.json')) if x['id']==$MJ];sys.exit(0 if j and j[0]['status'] in ('done','error') else 1)"; then break; fi
  sleep 1
done
python3 -c "
import json
j=[x for x in json.load(open('$OUT/jobs-music.json')) if x['id']==$MJ][0]
print('  ', j['status'], (j.get('result') or j.get('message') or '')[:300], '· took', $(date +%s) - $T0, 's')
assert j['status']=='done' and 'موسيقى' in j['result'], 'MUSIC REMOVAL FAILED'
print('music removal on the phone OK')"
log

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
