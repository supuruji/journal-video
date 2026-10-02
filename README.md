# journal-video

**One skill**: a journal issue (`.docx`/`.hwpx`) → paper-introduction videos, in **two designs**
and **three languages**, all from a single `content.json`.

- **Designs:** mind-map **film** + cinematic **scene reel** (도해)
- **Languages:** Korean / English / Chinese (한 · 英 · 中)
- **Output:** ready-to-upload **1920×1080 MP4** (headless render, embedded CLOVA narration),
  plus interactive mind maps and per-paper summaries.

```bash
python make.py content.json out --design both            # film + reel, all languages present
python make.py content.json out --design reel --langs ko,zh
```

Needs **Python 3, Node 18+, Google Chrome, ffmpeg** (no `npm install`). See **SKILL.md** for the
full workflow and the `content.json` schema.

> Merges the former **journal-issue-video** (mind-map) and **journal-scene-reel / 논문-도해영상**
> (scene reel) skills into one: the design is now a `--design` choice, the language a `--langs`
> choice, and both render from the same `content.json`.
