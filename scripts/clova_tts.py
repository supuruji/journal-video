# -*- coding: utf-8 -*-
"""
clova_tts.py — generate narration audio with NAVER Cloud CLOVA Voice (Premium)
and embed it into a map-film HTML so playback is gap-free with a real voice.

Credentials come from environment variables (never hard-code them):
  NCP_TTS_KEY_ID   = X-NCP-APIGW-API-KEY-ID
  NCP_TTS_KEY      = X-NCP-APIGW-API-KEY

Usage (PowerShell):
  $env:NCP_TTS_KEY_ID="..."; $env:NCP_TTS_KEY="..."
  python clova_tts.py <film.html> <speaker> [speed]
    <speaker>  e.g. clara, matt, danna, joey (EN) / nara, vara, jinho (KO)
    [speed]    -5..+5 (default 0; + = slower)

Needs: ffprobe (part of ffmpeg) on PATH to measure clip length. Standard library otherwise.
"""
import io, os, re, sys, json, base64, hashlib, subprocess, urllib.request, urllib.parse

ENDPOINT = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"

def strip_tags(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h or "")).strip()

def clova(text, speaker, speed, kid, key):
    body = urllib.parse.urlencode({
        "speaker": speaker, "text": text, "format": "mp3",
        "speed": str(speed), "volume": "0", "pitch": "0",
    }).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST")
    req.add_header("X-NCP-APIGW-API-KEY-ID", kid)
    req.add_header("X-NCP-APIGW-API-KEY", key)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def mp3_duration(path):
    try:
        out = subprocess.check_output(
            ["ffprobe","-v","error","-show_entries","format=duration",
             "-of","default=noprint_wrappers=1:nokey=1", path],
            stderr=subprocess.STDOUT).decode().strip()
        return float(out)
    except Exception:
        return None

# default narrator per language (overridable on the command line)
DEFAULT_SPEAKER = {"en": "matt", "ko": "nara", "zh": "meimei"}

def main():
    if len(sys.argv) < 2:
        print("usage: python clova_tts.py <film.html> [speaker] [speed]"); return
    html_path = sys.argv[1]
    speaker = sys.argv[2] if len(sys.argv) > 2 else None
    speed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    kid, key = os.environ.get("NCP_TTS_KEY_ID"), os.environ.get("NCP_TTS_KEY")
    if not kid or not key:
        print("!! Set NCP_TTS_KEY_ID and NCP_TTS_KEY environment variables first."); return

    h = io.open(html_path, "r", encoding="utf-8").read()
    m = re.search(r"const D = (.*?);\nconst RAW=", h, re.S)
    if not m:
        print("!! DATA block not found."); return
    data = json.loads(m.group(1))
    _dl = data.get("lang", "")
    lang = "ko" if _dl.startswith("ko") else ("zh" if _dl.startswith("zh") else "en")
    if not speaker:
        speaker = DEFAULT_SPEAKER[lang]
    print("Narrator:", speaker, "| lang:", lang)

    cache = {}            # text -> (dataUri, dur)
    cachedir = os.path.join(os.path.dirname(os.path.abspath(html_path)) or ".", "_clova_cache")
    os.makedirs(cachedir, exist_ok=True)
    total = 0
    for s in data.get("slides", []):
        for ln in s.get("lines", []):
            txt = strip_tags(ln["t"])
            if not txt:
                continue
            if txt in cache:
                uri, dur = cache[txt]
            else:
                mp3 = clova(txt, speaker, speed, kid, key)
                fn = os.path.join(cachedir, hashlib.md5(txt.encode("utf-8")).hexdigest()+".mp3")
                io.open(fn, "wb").write(mp3)
                dur = mp3_duration(fn)
                uri = "data:audio/mp3;base64," + base64.b64encode(mp3).decode("ascii")
                cache[txt] = (uri, dur)
                total += 1
                print("  [%2d] %4.1fs  %s" % (total, dur or 0, txt[:58]))
            ln["a"] = uri
            if dur:
                ln["d"] = int(dur*1000) + 550     # caption on-screen = clip + small tail
    newjson = json.dumps(data, ensure_ascii=False)
    h = h[:m.start()] + "const D = " + newjson + ";\nconst RAW=" + h[m.end():]
    io.open(html_path, "w", encoding="utf-8").write(h)
    print("Embedded %d audio clips into %s (%.1f MB)" % (total, os.path.basename(html_path), len(h)/1048576))

if __name__ == "__main__":
    main()
