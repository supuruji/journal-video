# -*- coding: utf-8 -*-
"""
make.py — one journal issue (.docx -> content.json) -> finished narrated MP4 videos,
in EITHER design and ANY of three languages, from a single content.json.

  design "mindmap"  -> video_film_<lang>.html  (animated mind-map film)
  design "reel"     -> scene_reel_<lang>.html   (cinematic scene reel / 도해)

Pipeline per (design, lang):
  build.py (content.json -> HTML) -> embed CLOVA narration -> headless render -> MP4

Usage:
  python make.py [content.json] [out_dir] [--design mindmap|reel|both]
                 [--langs ko,en,zh] [--no-narration] [--fps 30]

Requires: Python 3, Node 18+, Google Chrome, ffmpeg.
Narration needs NCP CLOVA keys in the environment:
  mindmap: NCP_TTS_KEY_ID / NCP_TTS_KEY     reel: NCP_CLIENT_ID / NCP_CLIENT_SECRET
Without keys (or --no-narration) the videos still render, but silent.
"""
import os, sys, io, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd, **kw):
    print("\n$ " + " ".join(str(c) for c in cmd)); subprocess.run(cmd, check=True, **kw)

def read(p): return io.open(p, "r", encoding="utf-8").read()
def write(p, s): io.open(p, "w", encoding="utf-8").write(s)

def main():
    args = sys.argv[1:]
    design, langs, narrate, fps, pos = "both", ["ko", "en", "zh"], True, "30", []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--design": design = args[i+1]; i += 2
        elif a == "--langs": langs = args[i+1].split(","); i += 2
        elif a == "--no-narration": narrate = False; i += 1
        elif a == "--fps": fps = args[i+1]; i += 2
        else: pos.append(a); i += 1
    content = pos[0] if len(pos) > 0 else "content.json"
    out_dir = pos[1] if len(pos) > 1 else "out"
    designs = ["mindmap", "reel"] if design == "both" else [design]

    py = sys.executable or "python"
    node = shutil.which("node") or sys.exit("!! Node.js (18+) not found on PATH.")
    if not shutil.which("ffmpeg"): sys.exit("!! ffmpeg not found on PATH.")

    tts_keys  = bool(os.environ.get("NCP_TTS_KEY_ID") and os.environ.get("NCP_TTS_KEY"))
    reel_keys = bool(os.environ.get("NCP_CLIENT_ID") and os.environ.get("NCP_CLIENT_SECRET"))

    # 1) build all HTML from the one content.json
    run([py, os.path.join(HERE, "build.py"), content, out_dir, os.path.join(HERE, "templates")])

    made = []
    for d in designs:
        prefix = "video_film" if d == "mindmap" else "scene_reel"
        for lang in langs:
            html = os.path.join(out_dir, "%s_%s.html" % (prefix, lang))
            if not os.path.exists(html):
                print("   (skip %s/%s: %s not built)" % (d, lang, os.path.basename(html))); continue
            # 2) narration (embed into the HTML)
            if narrate:
                if d == "mindmap" and tts_keys:
                    run([py, os.path.join(HERE, "scripts", "clova_tts.py"), html])
                elif d == "reel" and reel_keys:
                    ajs = os.path.join(out_dir, "_audio_%s.js" % lang)
                    run([py, os.path.join(HERE, "scripts", "clova_voice.py"),
                         "--html", html, "--lang", lang, "--out", ajs])
                    page, audio = read(html), read(ajs)
                    page = page.replace("<script>", "<script>\n" + audio + "\n</script>\n<script>", 1)
                    write(html, page); os.remove(ajs)
                else:
                    print("   (%s/%s: no CLOVA keys -> silent)" % (d, lang))
            # 3) render to MP4 (render_mp4.mjs auto-detects the player)
            mp4 = os.path.join(out_dir, "%s_%s.mp4" % (prefix, lang))
            run([node, os.path.join(HERE, "scripts", "render_mp4.mjs"), html, mp4, fps])
            made.append(mp4)

    print("\nDone. Videos:")
    for m in made:
        sz = os.path.getsize(m)/1e6 if os.path.exists(m) else 0
        print("  %s  (%.1f MB)" % (m, sz))
    if not made: sys.exit("!! Nothing rendered — check content.json / --design / --langs.")

if __name__ == "__main__":
    main()
