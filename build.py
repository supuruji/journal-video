# -*- coding: utf-8 -*-
"""
Journal Issue Video — build engine.

Reads one content.json describing a journal issue (metadata + papers, bilingual)
and renders a set of self-contained HTML artifacts:

  video_film_ko.html / video_film_en.html   : auto-playing "mind-map film" with narration
  mindmap_ko.html    / mindmap_en.html       : interactive tabbed mind-map reader
  summary_NN_<slug>.html                     : one bilingual summary per paper (abstract + read-aloud)

Usage:
  python build.py [content.json] [out_dir] [templates_dir]
Defaults: content.json=./content.json  out_dir=./out  templates_dir=./templates
"""
import io, os, re, sys, json

def read(p):   return io.open(p, "r", encoding="utf-8").read()
def write(p,s):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(s); print("  wrote", os.path.basename(p), "(%.1f KB)" % (len(s)/1024))

def slugify(s):
    s = re.sub(r"[^0-9A-Za-z가-힣]+", "-", s).strip("-")
    return s[:40] or "paper"

def split_sents(text):
    parts = re.split(r"(?<=[.!?。])\s+", (text or "").strip())
    return "".join('<span class="sent">%s</span> ' % p.strip() for p in parts if p.strip()).strip()

def chips(kw_list):
    return "".join('<span class="kw">%s</span>' % k for k in kw_list)

def surname(author):
    a = author.split("&")[0].strip()
    return a.split()[-1] if " " in a else a

# ---------- maps-page UI chrome (presentation only), per language ----------
def maps_ui(issue, lang):
    short = issue["journalShort"]; vol = issue["volume"]
    if lang == "ko":
        return dict(tag="논문 도해 · Mind Maps", theme="라이트/다크 전환",
            leadH1="여섯 편의 논문, 한눈에" if len(issue.get("_papers",[]))!=1 else "논문 한눈에",
            leadP=short+" "+vol+" · 각 논문의 <b>초록</b>을 핵심 구조로 풀어낸 마인드맵입니다. 위에서 논문을 고르세요.",
            fit="화면에 맞추기", fitBack="실제 크기",
            hintScroll="가지를 좌우·상하로 스크롤할 수 있습니다.",
            hintFit="화면 너비에 맞춰 축소했습니다. “실제 크기”로 크게 볼 수 있어요.",
            absLabel="초록 전문 보기 (English Abstract)", footName=issue["journalName"], articleTag="연구논문")
    if lang == "zh":
        return dict(tag="論文圖解 · Mind Maps", theme="明暗切換",
            leadH1=("六篇論文 · 一覽" if len(issue.get("_papers",[]))!=1 else "論文一覽"),
            leadP=short+" "+vol+" · 將每篇論文的<b>摘要</b>以核心結構展開的思維導圖。請在上方選擇論文。",
            fit="適應螢幕", fitBack="實際大小",
            hintScroll="可左右、上下捲動各分支。",
            hintFit="已按螢幕寬度縮小，可切換「實際大小」放大檢視。",
            absLabel="查看摘要全文 (English Abstract)", footName=issue["journalName"], articleTag="研究論文")
    return dict(tag="Paper Mind-Maps", theme="Toggle light/dark",
        leadH1="The papers at a glance",
        leadP=short+" "+vol+" · a mind map of each paper's <b>abstract</b>. Pick a paper above.",
        fit="Fit to screen", fitBack="Actual size",
        hintScroll="Scroll the branches horizontally and vertically.",
        hintFit="Scaled to fit the width — switch to “Actual size” to enlarge.",
        absLabel="Show full abstract", footName=issue["journalName"], articleTag="Research Article")

# ---------- assemble DATA for the video-film template ----------
def video_data(content, lang):
    issue = content["issue"]; papers = content["papers"]
    rate = 1.0 if lang == "ko" else 0.98
    sec = lambda name: issue[name][lang]
    slides = []
    c = sec("cover")
    slides.append(dict(kind="cover", accent=0, name=c["name"], vol=issue["volume"],
        sub=c["sub"], issuebar=c["issuebar"], lines=c["lines"]))
    a = sec("about")
    slides.append(dict(kind="text", accent=1, name=a["name"], eyebrow=a["eyebrow"],
        lead=a["lead"], attr=a.get("attr",""), lines=a["lines"]))
    co = sec("counts")
    slides.append(dict(kind="counts", accent=2, name=co["name"], eyebrow=co["eyebrow"],
        stats=co["stats"], points=co["points"], lines=co["lines"]))
    for p in papers:
        mm = p["mindmap"][lang]
        slides.append(dict(kind="map", accent=p["accent"], num=p["num"],
            name=issue["articleName"][lang] % (p["num"], surname(p["author"])),
            eyebrow=issue["articleEyebrow"][lang], titleEn=p["titleEn"], author=p["author"],
            aff=p["aff"], page=p["page"], root=mm["root"], branches=mm["branches"],
            lines=p["narration"][lang]))
    r = sec("reviews")
    slides.append(dict(kind="reviews", accent=2, name=r["name"], eyebrow=r["eyebrow"],
        items=r["items"], lines=r["lines"]))
    cl = sec("closing")
    slides.append(dict(kind="closing", accent=0, name=cl["name"], eyebrow=cl["eyebrow"],
        lead=cl["lead"], attr=cl.get("attr",""), thanks=cl.get("thanks",""),
        site=issue["site"], lines=cl["lines"]))
    return dict(logo=issue["logoDataUri"], lang=("ko-KR" if lang=="ko" else ("zh-CN" if lang=="zh" else "en-US")),
                rate=rate, ui=issue["ui"][lang], slides=slides)

# ---------- assemble DATA for the mindmap-tabs template ----------
def maps_data(content, lang):
    issue = content["issue"]
    issue["_papers"] = content["papers"]
    ps = []
    for p in content["papers"]:
        mm = p["mindmap"][lang]
        ps.append(dict(num=p["num"], accent=p["accent"], short=p["short"][lang],
            titleEn=p["titleEn"], author=p["author"], aff=p["aff"], page=p["page"],
            root=mm["root"], branches=mm["branches"], kw=p.get("keywords",[]), abstract=p["abstract"]))
    return dict(logo=issue["logoDataUri"], site=issue["site"], ui=maps_ui(issue, lang), papers=ps)


# ========================= scene-reel (도해) design =========================
REEL_UI = {
  "ko": {"play":"재생","pause":"정지","full":"전체화면","prev":"이전","next":"다음","son":"음성 켜짐","soff":"음소거"},
  "zh": {"play":"播放","pause":"暂停","full":"全屏","prev":"上一张","next":"下一张","son":"語音開","soff":"靜音"},
  "en": {"play":"Play","pause":"Pause","full":"Fullscreen","prev":"Prev","next":"Next","son":"Sound on","soff":"Muted"},
}
REEL_LANGS = ("ko", "en", "zh")

def _plain(x):
    return re.sub(r"<[^>]+>", "", x or "").strip()

def _reel_thesis(p, lang):
    nar = (p.get("narration", {}) or {}).get(lang) or []
    if nar:
        return _plain(nar[0].get("t", ""))
    if lang == "ko" and p.get("ednoteKo"):
        return p["ednoteKo"]
    return p.get("summaryKo", "") if lang == "ko" else p["titleEn"]

def reel_papers(content):
    out = []
    for p in content["papers"]:
        r = p.get("reel", {}) or {}
        tag, t, s, who = {}, {}, {}, {}
        for lang in REEL_LANGS:
            tag[lang] = (r.get("tag", {}) or {}).get(lang) or (p.get("short", {}) or {}).get(lang) or p["titleEn"]
            t[lang]   = (r.get("title", {}) or {}).get(lang) or (p.get("short", {}) or {}).get(lang) or p["titleEn"]
            s[lang]   = (r.get("thesis", {}) or {}).get(lang) or _reel_thesis(p, lang)
            who[lang] = (r.get("who", {}) or {}).get(lang) or p["author"]
        n = int(re.sub(r"\D", "", str(p.get("num", "0"))) or 0)
        out.append(dict(n=n, tag=tag, en=p["titleEn"], who=who,
                        lat=r.get("lat") or p["author"], aff=p.get("aff", ""), t=t, s=s))
    return out

def reel_copy(content):
    iss = content["issue"]; r = iss.get("reel", {}) or {}
    npapers = len(content["papers"])
    short = iss["journalShort"]; vol = iss["volume"]; year = iss.get("year", ""); jname = iss["journalName"]
    KICK  = {"ko":"이번 호", "zh":"本期", "en":"This issue"}
    LABEL = {"ko":"편의 학술논문 · Research Articles", "zh":"篇 學術論文 · Research Articles", "en":"Research Articles"}
    THANKS= {"ko":"읽어주셔서 감사합니다", "zh":"感謝閱讀", "en":"Thank you for reading"}
    copy = {}
    for lang in REEL_LANGS:
        c = dict((r.get("copy", {}) or {}).get(lang, {}))
        cov = (iss.get("cover", {}).get(lang, {}) or {})
        ab  = (iss.get("about", {}).get(lang, {}) or {})
        cl  = (iss.get("closing", {}).get(lang, {}) or {})
        pub = (r.get("publisher", {}) or {}).get(lang, "")
        c.setdefault("titleKicker", r.get("academy", "Daesoon Academy of Sciences"))
        c.setdefault("titleBig", jname)
        c.setdefault("titleSub", cov.get("sub") or cov.get("name") or "")
        c.setdefault("titleVol", vol + ((" — " + year) if year else ""))
        c.setdefault("titlePub", pub)
        c.setdefault("ovKicker", KICK[lang])
        c.setdefault("ovCount", str(npapers))
        c.setdefault("ovLabel", LABEL[lang])
        c.setdefault("ovLead", ab.get("lead") or (iss.get("counts", {}).get(lang, {}) or {}).get("points", ""))
        c.setdefault("clKicker", THANKS[lang])
        c.setdefault("clBig", short + " " + vol)
        c.setdefault("clSub", cl.get("thanks") or cl.get("lead") or "")
        c.setdefault("clPub", pub)
        c.setdefault("titleNarr", ". ".join(x for x in [_plain(c["titleBig"]), _plain(c["titleVol"]), _plain(c["titleSub"])] if x) + ".")
        c.setdefault("ovNarr", _plain(c["ovLead"]))
        c.setdefault("clNarr", _plain(c["clSub"]) or _plain(c["clKicker"]))
        copy[lang] = c
    return copy

def reel_editor(content):
    iss = content["issue"]; r = iss.get("reel", {}) or {}
    if r.get("editor"):
        return r["editor"]
    return {"who": {"ko":"", "zh":"", "en":""}, "role": {"ko":"", "zh":"", "en":""}, "date": iss.get("year", "")}

def reel_data(content, start_lang):
    iss = content["issue"]
    return dict(ui=REEL_UI, papers=reel_papers(content), editor=reel_editor(content),
                copy=reel_copy(content), startLang=start_lang,
                brandShort=iss["journalShort"], brand=iss["journalName"])


def main():
    content_path = sys.argv[1] if len(sys.argv) > 1 else "content.json"
    out_dir      = sys.argv[2] if len(sys.argv) > 2 else "out"
    tpl_dir      = sys.argv[3] if len(sys.argv) > 3 else "templates"
    content = json.loads(read(content_path))
    issue = content["issue"]; short = issue["journalShort"]; vol = issue["volume"]
    pal = issue.get("accentPalette", ["#9a5cc4","#c74da0","#28b2c4","#ef7a4e","#7a6bd6","#e6b24a"])

    T_video = read(os.path.join(tpl_dir, "video_film.html"))
    T_maps  = read(os.path.join(tpl_dir, "mindmap_tabs.html"))
    T_paper = read(os.path.join(tpl_dir, "paper_summary.html"))

    def put(tpl, title, desc, data):
        return tpl.replace("__TITLE__", title).replace("__DESC__", desc)\
                  .replace("__DATA__", json.dumps(data, ensure_ascii=False))

    print("Rendering", short, vol, "->", out_dir)
    # videos
    write(os.path.join(out_dir, "video_film_ko.html"),
          put(T_video, short+" 논문 도해 영상", short+" "+vol+" 논문 도해 + 음성 내레이션 (한국어)", video_data(content,"ko")))
    write(os.path.join(out_dir, "video_film_en.html"),
          put(T_video, short+" Mind-Map Film", short+" "+vol+" paper mind-map video with narration (English)", video_data(content,"en")))
    _has_zh = "zh" in content["issue"].get("cover", {})
    if _has_zh:
        write(os.path.join(out_dir, "video_film_zh.html"),
              put(T_video, short+" 論文圖解影片", short+" "+vol+" 論文思維導圖影片（中文）", video_data(content,"zh")))
    # tabbed mind maps
    write(os.path.join(out_dir, "mindmap_ko.html"),
          put(T_maps, short+" 논문 도해", short+" "+vol+" 논문 마인드맵 (한국어)", maps_data(content,"ko")))
    write(os.path.join(out_dir, "mindmap_en.html"),
          put(T_maps, short+" Mind Maps", short+" "+vol+" paper mind maps (English)", maps_data(content,"en")))
    if _has_zh:
        write(os.path.join(out_dir, "mindmap_zh.html"),
              put(T_maps, short+" 論文圖解", short+" "+vol+" 論文思維導圖（中文）", maps_data(content,"zh")))

    # ---- scene-reel (도해) design: content.json -> scene_reel_<lang>.html ----
    T_reel = read(os.path.join(tpl_dir, "scene-reel.template.html"))
    for _lang, _label in [("ko", "한국어"), ("en", "English")] + ([("zh", "中文")] if _has_zh else []):
        write(os.path.join(out_dir, "scene_reel_%s.html" % _lang),
              put(T_reel, short + " 도해 영상 " + _label,
                  short + " " + vol + " scene-reel 도해 (" + _label + ")", reel_data(content, _lang)))
    # per-paper bilingual summaries
    for p in content["papers"]:
        a1 = pal[p["accent"] % len(pal)]; a2 = pal[(p["accent"]+1) % len(pal)]
        repl = {
          "__TITLE__": p["num"]+" "+surname(p["author"])+" · "+p["short"]["ko"],
          "__A1__": a1, "__A2__": a2, "__NUM__": p["num"], "__PAGE__": p["page"],
          "__TITLE_EN__": p["titleEn"], "__AUTHOR__": p["author"], "__AFF__": p["aff"],
          "__KEYWORDS__": chips(p.get("keywords",[])),
          "__ABSTRACT__": split_sents(p["abstract"]),
          "__SUMMARY__": split_sents(p.get("summaryKo","")),
          "__EDNOTE__": p.get("ednoteKo",""), "__LOGO__": issue["logoDataUri"],
        }
        html = T_paper
        for k,v in repl.items(): html = html.replace(k, v)
        write(os.path.join(out_dir, "summary_%s_%s.html" % (p["num"], slugify(surname(p["author"])))), html)
    print("Done.")

if __name__ == "__main__":
    main()
