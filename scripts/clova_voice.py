#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 클로바 보이스(CLOVA Voice, NCP)로 '도해 영상'의 중국어 장면 내레이션 mp3를 생성하고,
HTML에 인라인으로 주입할 수 있는 스니펫(window.__ZH_AUDIO = {...})을 만든다.

- 인증키는 '파일'에서만 읽고(화면에 출력하지 않음), 외부로 보내지 않는다(클로바 API 호출에만 사용).
- 내레이션 문구는 빌드된 HTML(scene-reel)에서 중국어 장면 텍스트를 그대로 추출해 사용한다.

사용법:
  python clova_voice.py --html "<빌드된.html>" --keyfile "<clova_key.txt>" \
         --speaker meimei --out "<zh_audio.js>" [--speed 0]

clova_key.txt 형식(2줄):
  첫 줄 = Client ID (X-NCP-APIGW-API-KEY-ID)
  둘째 줄 = Client Secret (X-NCP-APIGW-API-KEY)
(또는 환경변수 NCP_CLIENT_ID / NCP_CLIENT_SECRET 사용)

출력: zh_audio.js  →  window.__ZH_AUDIO = { "0":"data:audio/mp3;base64,...", ... };
이 파일 내용을 <script>...</script> 로 HTML(중문/통합본)의 메인 스크립트 앞에 인라인 주입한다.
"""
import sys, os, re, json, base64, argparse, urllib.request, urllib.parse

TTS_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"

def read_keys(keyfile):
    cid = os.environ.get("NCP_CLIENT_ID")
    csec = os.environ.get("NCP_CLIENT_SECRET")
    if cid and csec:
        return cid.strip(), csec.strip()
    if keyfile and os.path.exists(keyfile):
        lines = [l.strip() for l in open(keyfile, encoding="utf-8") if l.strip()]
        if len(lines) >= 2:
            return lines[0], lines[1]
    sys.exit("ERROR: 인증키를 찾을 수 없습니다. --keyfile(2줄: ID/Secret) 또는 "
             "환경변수 NCP_CLIENT_ID/NCP_CLIENT_SECRET 를 설정하세요.")

def clean(t):
    t = re.sub(r"[《》〈〉「」『』]", "", t)
    t = re.sub(r"\s*[—–-]\s*", " , ", t)
    t = re.sub(r"\([㐀-鿿]+\)", "", t)
    t = re.sub(r"（[㐀-鿿]+）", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t

# 고정 멘트: narrText()의 각 언어 분기와 동일해야 한다.
FIXED = {
  "zh": {
    "title":    "東亞宗教文化研究。第三卷 第二期。二〇二六年六月。大眞大學 大巡思想學術院 出版。",
    "overview": "本期收錄十七篇學術論文，呈現跨文明、跨文本、跨學科的研究色彩。",
    "closing":  "全十七篇，以中文、韓文、英文線上公開。主編 李紅軍。二〇二六年六月三十日。",
    "nth": lambda n: f"第{n}篇。",
  },
  "ko": {
    "title":    "동아시아 종교문화 연구. 제 3권 2호. 2026년 6월. 대진대학교 대순사상학술원 발간.",
    "overview": "이번 호에는 열일곱 편의 학술논문을 수록하여, 문명과 텍스트와 학문을 가로지르는 연구 색채를 담았습니다.",
    "closing":  "전 열일곱 편. 중국어 한국어 영어로 온라인 공개됩니다. 주간 이홍군. 2026년 6월 30일.",
    "nth": lambda n: f"{n}번. ",
  },
  "en": {
    "title":    "East Asian Religions and Cultures. Volume three, issue two. June 2026. Published by the Daesoon Academy of Sciences, Daejin University.",
    "overview": "This issue presents seventeen research articles with a cross-civilizational, cross-textual and cross-disciplinary character.",
    "closing":  "All seventeen papers, published online in Chinese, Korean and English. Editor-in-chief, Li Hongjun. June thirtieth, 2026.",
    "nth": lambda n: f"No. {n}. ",
  },
}

def extract_narration(html, lang):
    """데이터 구동 scene-reel HTML에서 주입된 const D = {..}(__DATA__)를 파싱해 장면 내레이션 리스트를 만든다."""
    m = re.search(r"const D\s*=\s*(\{.*?\});\s*\nconst COPY", html, re.S)
    if not m:
        sys.exit("ERROR: HTML에서 const D(__DATA__) 블록을 찾지 못했습니다. build.py로 생성한 scene_reel_*.html인지 확인하세요.")
    D = json.loads(m.group(1))
    copy = (D.get("copy", {}) or {}).get(lang, {})
    papers = D.get("papers", [])
    nthf = {"ko": (lambda n: "%s번. " % n), "zh": (lambda n: "第%s篇。" % n), "en": (lambda n: "No. %s. " % n)}.get(lang, lambda n: "%s. " % n)
    scenes = [copy.get("titleNarr", ""), copy.get("ovNarr", "")]
    for pp in papers:
        t = (pp.get("t", {}) or {}).get(lang) or pp.get("en", "")
        sv = (pp.get("s", {}) or {}).get(lang) or ""
        scenes.append(clean(nthf(pp.get("n", "?")) + t + ". " + sv))
    scenes.append(copy.get("clNarr", ""))
    return scenes
def tts(text, cid, csec, speaker, speed):
    data = urllib.parse.urlencode({
        "speaker": speaker, "text": text,
        "format": "mp3", "speed": str(speed), "volume": "0", "pitch": "0",
    }).encode("utf-8")
    req = urllib.request.Request(TTS_URL, data=data, method="POST")
    req.add_header("X-NCP-APIGW-API-KEY-ID", cid)
    req.add_header("X-NCP-APIGW-API-KEY", csec)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--keyfile", default="")
    ap.add_argument("--lang", default="zh", choices=["zh", "ko", "en"])
    ap.add_argument("--speaker", default="")
    ap.add_argument("--speed", default="0")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if not a.speaker:
        a.speaker = {"ko": "nara", "zh": "meimei", "en": "matt"}.get(a.lang, "meimei")

    cid, csec = read_keys(a.keyfile)
    html = open(a.html, encoding="utf-8").read()
    scenes = extract_narration(html, a.lang)
    print(f"장면 {len(scenes)}개 {a.lang} 내레이션 생성 (speaker={a.speaker}) ...")

    audio = {}
    for i, txt in enumerate(scenes):
        try:
            mp3 = tts(txt, cid, csec, a.speaker, a.speed)
        except urllib.error.HTTPError as ex:
            body = ex.read().decode("utf-8", "ignore")[:300]
            sys.exit(f"ERROR: CLOVA {ex.code} on scene {i}: {body}")
        audio[str(i)] = "data:audio/mp3;base64," + base64.b64encode(mp3).decode("ascii")
        print(f"  [{i:02d}] {len(mp3)//1024}KB  {txt[:28]}...")

    varname = {"ko": "__KO_AUDIO", "en": "__EN_AUDIO"}.get(a.lang, "__ZH_AUDIO")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("window." + varname + " = " + json.dumps(audio, ensure_ascii=True) + ";\n")
    total = sum(len(v) for v in audio.values()) // 1024
    print(f"완료: {a.out}  (window.{varname}, 총 {total}KB, base64)")

if __name__ == "__main__":
    main()
