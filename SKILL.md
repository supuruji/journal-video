---
name: journal-video
description: >-
  One skill that turns an academic journal issue — a .docx (or .hwpx) with an editor's/
  translator's preface and article abstracts — into a finished, narrated "paper introduction"
  VIDEO, in EITHER of two designs and ANY of three languages, all from a single content.json:
  (1) a mind-map FILM and (2) a cinematic scene-reel 도해. Each renders to ready-to-upload
  1920x1080 MP4s in Korean, English and/or Chinese, plus interactive mind maps and per-paper
  summaries. `make.py --design mindmap|reel|both` runs the whole pipeline end to end (build
  HTML -> embed CLOVA narration -> headless render to MP4). Good for JDTREA, JEARC and any
  issue-based journal. Trigger on "논문/저널 docx로 소개 영상 / 도해·마인드맵 영상 / 중문·영문·한글
  영상 / 유튜브 올릴 mp4 / 권 전체 소개 영상".
---

# Journal Video (마인드맵 + 도해 통합)

Turn **one** journal-issue `.docx` into paper-introduction videos. Pick the **design** and the
**language(s)** — both come from the **same `content.json`**.

| Design (`--design`) | Output files | What it is |
|---|---|---|
| **`mindmap`** | `video_film_<lang>.html` → `.mp4` | Auto-playing film: cover → preface → each paper as an animated **mind map** → reviews → closing. |
| **`reel`** | `scene_reel_<lang>.html` → `.mp4` | Cinematic **scene reel** (도해): title → overview → one card per paper (tag · title · one-line thesis · author) → closing. |
| (both also emit) | `mindmap_<lang>.html`, `summary_NN_*.html` | Interactive tabbed mind maps + per-paper bilingual summaries. |

`<lang>` ∈ **ko / en / zh**. Everything is self-contained (logo embedded, Google Fonts incl.
Noto Sans/Serif **SC** for Chinese); narration is embedded CLOVA audio or browser TTS.

## How to use (workflow)

1. **Extract.** `python scripts/extract_docx.py "<issue>.docx"` → preface + every abstract/keywords.
2. **Author `content.json`.** Copy `examples/content.jdtrea-5-2.json`. Fill `ko`, `en` and (optional)
   `zh` for each text field. For each paper: a mind-map tree (`mindmap`, `root` + 3–5 `branches`)
   and narration `lines` for the **film**; the **reel** reuses the same paper fields and falls back
   gracefully, or you can give per-paper `reel` fields for a tailored reel (see Schema).
3. **Make the videos (one command).**
   ```bash
   python make.py content.json out --design both            # all: film + reel, every lang present
   python make.py content.json out --design reel --langs ko,zh
   python make.py content.json out --design mindmap --langs en
   ```
   Builds the HTML, embeds CLOVA narration, and headless-renders **`out/<prefix>_<lang>.mp4`**.
   Flags: `--design mindmap|reel|both`, `--langs ko,en,zh`, `--no-narration`, `--fps 30`.
   `zh` is emitted only when the content carries `zh` fields.
4. **Deliver.** Upload the MP4s to YouTube (sign in to the target channel first; audience
   "not made for kids"; public uploads are hard to undo — confirm account + visibility).

To regenerate after edits, re-run step 3.

## Schema (content.json)

The base schema is the mind-map one (issue + per-paper `titleEn`, `author`, `aff`, `short{lang}`,
`mindmap{lang}`, `narration{lang}`, `abstract`, `keywords`, …). The **reel** design adds OPTIONAL
fields; when omitted it falls back to the mind-map fields:

```jsonc
"papers": [{
  "num":"01", "titleEn":"…", "author":"SHEN Yeh-Ying", "aff":"…",
  "short": { "ko":"…", "en":"…", "zh":"…" },         // reel tag/title fall back to this
  "mindmap": { "ko": { "root","branches" }, "en":{…}, "zh":{…} },
  "narration": { "ko":[{"t","d"}], "en":[…], "zh":[…] },   // reel thesis falls back to narration[0]
  "reel": {                                           // OPTIONAL — tailor the reel card
     "tag":    { "ko":"분야", "en":"Field", "zh":"領域" },
     "title":  { "ko":"제목", "en":"Title", "zh":"標題" },
     "thesis": { "ko":"핵심 논지 한 줄", "en":"…", "zh":"…" },
     "who":    { "ko":"저자(한글)", "en":"Author", "zh":"作者" }, "lat":"ROMANIZED"
  }
}],
"issue": {
  "journalName":"…", "journalShort":"JDTREA", "volume":"Vol. 5 · No. 2", "year":"2025",
  "ui":{…}, "cover":{…}, "about":{…}, "counts":{…}, "reviews":{…}, "closing":{…},
  "reel": {                                           // OPTIONAL — reel fixed-scene copy / editor
     "academy":"Daesoon Academy of Sciences",
     "publisher": { "ko":"…", "en":"…", "zh":"…" },
     "editor":    { "who":{lang}, "role":{lang}, "date":"2025" },
     "copy":      { "ko":{ "titleSub","ovLead","clSub", … }, "en":{…}, "zh":{…} }  // override any fixed string
  }
}
```

Notes
- Give a field a `zh` value to also emit the Chinese versions (`*_zh.html`/`.mp4`).
- Reel `tag`←`short`, `title`←`short`/`titleEn`, `thesis`←`narration[0]`/`ednoteKo`, `who`←`author`
  when the `reel` block is absent. Provide `reel` for a hand-tuned card.
- Inline HTML allowed in copy/thesis: `<b>…</b>`, `<span class="hl">…</span>`.

## Narration (NAVER CLOVA Voice — optional, recommended)

- **mindmap**: `scripts/clova_tts.py` (keys `NCP_TTS_KEY_ID`/`NCP_TTS_KEY`; narrators en=`matt`,
  ko=`nara`, zh=`meimei`) embeds per-line MP3 into the film in place.
- **reel**: `scripts/clova_voice.py` (keys `NCP_CLIENT_ID`/`NCP_CLIENT_SECRET`) reads the built
  reel's data, makes one MP3 per scene, and `make.py` injects it as `window.__{KO,EN,ZH}_AUDIO`.
- `make.py` does both automatically when keys are set; without them the videos render **silent**.

## Rendering to MP4 (headless — no screen recording)

`scripts/render_mp4.mjs <film.html> [out.mp4] [fps]` opens the HTML in a **headless** Chrome,
captures it in real time, rebuilds narration from the embedded clips, and muxes a 1920×1080/30fps
MP4. It **auto-detects both players** (mind-map film and scene reel) and hides on-screen controls.
Node 18+/Chrome/ffmpeg, no `npm install`. Never screen-record (it catches other windows, breaks on
pop-ups, and fails on multi-monitor). `scripts/render_video.py` is an alternative static per-scene
renderer for the reel.

## Charset

Templates start with `<!DOCTYPE html>` + `<meta charset="utf-8">` and the renderer serves UTF-8,
so Korean/Chinese never fall back to EUC-KR mojibake.

## Files
- `make.py` — one-shot driver (content.json → build → narrate → MP4; `--design`, `--langs`).
- `build.py` — renders both designs' HTML from one content.json (stdlib only).
- `templates/` — `video_film.html` (mindmap film), `scene-reel.template.html` (reel, data-driven),
  `mindmap_tabs.html`, `paper_summary.html`.
- `scripts/` — `extract_docx.py`, `clova_tts.py` (film TTS), `clova_voice.py` (reel TTS),
  `render_mp4.mjs` (headless renderer, both players), `render_video.py` (static reel renderer).
- `examples/content.jdtrea-5-2.json` — a complete working example.
