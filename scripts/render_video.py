# -*- coding: utf-8 -*-
"""
도해 HTML을 1920×1080 MP4로 렌더링한다. (화면 녹화 없이 결정론적 합성)
각 장면을 헤드리스 Chrome으로 정적 캡처(#shot{n}) → 클로바/TTS mp3와 ffmpeg로 합성 → 이어붙이기.

필요: ffmpeg/ffprobe, Chrome(또는 Edge) 헤드리스.

사용법(언어 1개당 1회):
  python render_video.py --base-html "<엔진+데이터(오디오 미주입).html>" --lang ko \
      --audio "<ko_audio.js>" --out "<결과.mp4>" --workdir "<작업폴더>"
옵션:
  --audio 생략 시 각 장면을 --seconds(기본 7초) 무음으로.  --scenes N (오디오 없을 때 장면 수).
  --chrome "<chrome.exe 경로>" (미지정 시 자동 탐색).  --fps 30.

base-html: scene-reel 템플릿에 데이터를 넣은 '빌드본'이되, window.__ZH_AUDIO/__KO_AUDIO 가
          인라인 주입되지 '않은' 상태를 권장(프레임은 정적 캡처라 오디오 불필요).
"""
import os, sys, json, base64, argparse, subprocess, re, tempfile

CHROME_CANDIDATES = [
    r"C:/Program Files/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    r"C:/Program Files/Microsoft/Edge/Application/msedge.exe",
]

def find_chrome(p):
    if p and os.path.exists(p): return p
    for c in CHROME_CANDIDATES:
        if os.path.exists(c): return c
    sys.exit("ERROR: Chrome/Edge 실행파일을 찾지 못했습니다. --chrome 로 지정하세요.")

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write("FAIL %s\n%s\n" % (cmd[:3], r.stderr[-700:]))
    return r.returncode

def dur_of(path):
    return float(subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1", path]).decode().strip())

def load_audio_js(js_path, workdir, lang):
    t = open(js_path, encoding="utf-8").read()
    d = json.loads(t[t.index("{"):t.rindex("}")+1])
    mp3s = {}
    for k, v in d.items():
        b = base64.b64decode(v.split(",",1)[1])
        fp = os.path.join(workdir, f"aud_{lang}_{int(k):02d}.mp3")
        open(fp, "wb").write(b)
        mp3s[int(k)] = fp
    return mp3s

def make_frame_html(base_html, lang, workdir):
    html = open(base_html, encoding="utf-8").read()
    marker = "<script>\n/* ======"
    if marker not in html:
        marker = "<script>"   # 폴백
    inj = '<script>window.__START_LANG="%s";</script>\n' % lang
    out = os.path.join(workdir, f"frame_{lang}.html")
    open(out, "w", encoding="utf-8").write(html.replace(marker, inj+marker, 1))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-html", required=True)
    ap.add_argument("--lang", default="ko")
    ap.add_argument("--audio", default="")
    ap.add_argument("--scenes", type=int, default=0)
    ap.add_argument("--seconds", type=float, default=7.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--chrome", default="")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--tail", type=float, default=0.6)
    a = ap.parse_args()

    chrome = find_chrome(a.chrome)
    os.makedirs(a.workdir, exist_ok=True)
    frame_html = make_frame_html(a.base_html, a.lang, a.workdir)

    mp3s = load_audio_js(a.audio, a.workdir, a.lang) if a.audio else {}
    N = len(mp3s) if mp3s else a.scenes
    if N <= 0:
        sys.exit("ERROR: 장면 수를 알 수 없습니다. --audio 또는 --scenes 를 주세요.")

    url_base = "file:///" + frame_html.replace("\\", "/")
    clips = []
    for i in range(N):
        png = os.path.join(a.workdir, f"frm_{a.lang}_{i:02d}.png")
        run([chrome,"--headless=new","--disable-gpu","--hide-scrollbars",
             "--force-device-scale-factor=1","--window-size=1920,1080",
             "--virtual-time-budget=9000", f"--screenshot={png}", f"{url_base}#shot{i}"])
        if not os.path.exists(png):
            print(f"  !! frame {i} 실패"); continue
        clip = os.path.join(a.workdir, f"clip_{a.lang}_{i:02d}.mp4")
        if i in mp3s:
            d = dur_of(mp3s[i]); total = d + a.tail
            vf = f"fade=t=in:st=0:d=0.5,fade=t=out:st={max(0,total-0.45):.2f}:d=0.45,format=yuv420p"
            af = f"afade=t=in:st=0:d=0.2,afade=t=out:st={max(0,d-0.3):.2f}:d=0.3,apad"
            rc = run(["ffmpeg","-y","-loop","1","-framerate",str(a.fps),"-i",png,"-i",mp3s[i],
                "-t",f"{total:.2f}","-vf",vf,"-af",af,
                "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
                "-c:a","aac","-b:a","192k","-ar","44100","-ac","2","-r",str(a.fps),
                "-video_track_timescale","15360", clip])
        else:
            total = a.seconds
            vf = f"fade=t=in:st=0:d=0.5,fade=t=out:st={max(0,total-0.45):.2f}:d=0.45,format=yuv420p"
            rc = run(["ffmpeg","-y","-loop","1","-framerate",str(a.fps),"-i",png,
                "-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t",f"{total:.2f}","-vf",vf,
                "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
                "-c:a","aac","-b:a","192k","-ar","44100","-ac","2","-r",str(a.fps),
                "-video_track_timescale","15360", clip])
        if os.path.exists(clip): clips.append(clip)

    listf = os.path.join(a.workdir, f"list_{a.lang}.txt")
    with open(listf,"w",encoding="utf-8") as f:
        for c in clips: f.write("file '%s'\n" % c.replace("\\","/").replace("'", r"'\''"))
    rc = run(["ffmpeg","-y","-f","concat","-safe","0","-i",listf,"-c","copy",a.out])
    if rc != 0 or not os.path.exists(a.out):
        run(["ffmpeg","-y","-f","concat","-safe","0","-i",listf,
             "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
             "-c:a","aac","-b:a","192k","-ar","44100", a.out])
    if os.path.exists(a.out):
        print(f"완료: {a.out}  ({os.path.getsize(a.out)//1048576}MB, {dur_of(a.out):.1f}s, {len(clips)}장면)")
    else:
        print("최종 생성 실패")

if __name__ == "__main__":
    main()
