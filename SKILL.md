-------
name: excalidraw-video-maker
description: Create or revise narrated vertical videos using .excalidrawlib drawings, original SVG or PNG logos, SRT subtitles, and voice-over audio. Use for Excalidraw whiteboard or explainer videos, section visuals, subtitle retiming, and audio-led scene assembly.
---

# Excalidraw Video Maker

Build editable, narration-led videos from the user's own visual assets. Keep each video's storyboard and source files together so later sections can retain the same style.

## Workflow

1. Locate the supplied `.excalidrawlib`, SVG/PNG logos, SRT, and narration. If a referenced file lives in the user's Library, materialize it before working. Never invent a logo or silently substitute a lookalike for a requested original mark.
2. Inspect each library item before using it. The bundled renderer supports Excalidraw rectangles, ellipses, diamonds, lines, arrows, and free draw strokes. If an item contains text, images, frames, or complex bindings, export the item from Excalidraw as SVG/PNG and reference that file instead. Preserve the original item's proportions and legibility.
3. Check SRT cues for complete text, ordered nonoverlapping times, reading comfort, and repeated sentences. Match scene boundaries to the **actual spoken audio**. If narration is too fast, generate or edit a naturally paced take and lengthen the video/SRT; do not squeeze the speech or shorten the user's script. When replacing a repeated phrase, remove the old audio span before inserting the clean take, then check that the replacement is spoken once.
4. Build a JSON storyboard with one scene per SRT cue. Use `scripts/render_video.py` for a simple vertical explainer. Read [storyboard-format.md](references/storyboard-format.md) for the fields and example. For elaborate scene layouts, write a custom frame function around the same cue timeline; keep the storyboard as the source of scene intent.
5. Put a small, consistent chapter icon in an unused corner for each chapter. Keep brand logos in their native colors. Preview several frames, including every chapter boundary, and check that icon, title, caption, and logo never collide or clip on a phone screen.
6. Render 720×1280 H.264/AAC MP4, preserve SRT as a separate deliverable, and optionally deliver an audio-only file. Use the original voice at normal speed. Verify MP4/audio duration and final SRT end, inspect the last spoken phrase, and give the user the video and SRT files.

## Reusable renderer

Run from any working directory; paths inside the JSON resolve relative to that JSON file:

```bash
python3 <skill-dir>/scripts/render_video.py storyboard.json --preview contact.png
python3 <skill-dir>/scripts/render_video.py storyboard.json --output video.mp4
```

Requirements: Python Pillow, FFmpeg/ffprobe, Inkscape for SVG rasterization, and a Myanmar Unicode font. The renderer draws a restrained title, illustration, optional two logo cards, chapter badge, and caption. It validates cue ordering, scene count, caption fit, and voice/SRT duration. Adjust layout or write a custom frame renderer when the content needs more than this template.

Save final video, SRT, voice, and any reusable storyboard/project source in the user's persistent files. Keep generated preview frames and temporary encoding files out of final deliverables.
