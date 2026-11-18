# Storyboard JSON

Use one `scenes` entry for each cue in the external SRT. All relative paths resolve from the JSON's folder.

```json
{
  "srt": "subtitles.srt",
  "voice": "narration.mp3",
  "brand": "AI TOOLS BY DAVID",
  "background": "#F7F5ED",
  "ink": "#18334A",
  "accent": "#26A7A1",
  "fps": 24,
  "scenes": [
    {
      "title": "Chatbot ကို သုံးတဲ့ပုံ",
      "subtitle": "လူက စာကူးပြီး AI ကို မေးမယ်",
      "icon": {"library": "robots.excalidrawlib", "index": 2, "color": "#18334A"},
      "badge": {"library": "robots.excalidrawlib", "index": 2, "color": "#18334A"},
      "logos": [
        {"path": "chatgpt.svg", "label": "ChatGPT"},
        {"path": "claude.svg", "label": "Claude"}
      ],
      "bullets": ["စာကို AI ထဲ ထည့်မယ်"]
    }
  ]
}
```

`icon` and `badge` may instead be `{"path": "drawing.svg"}` or a PNG path. `logos`, `bullets`, and `subtitle` are optional. Keep `title` short. The template allows two logo cards, three short bullets, and up to four caption lines. The SRT supplies both caption text and scene timing; the voice file supplies the actual narration. The final SRT end must match audio duration within half a second. Do not modify voice speed to force a match.

For complex Excalidraw art, export the complete item from Excalidraw as SVG/PNG. The library parser handles only basic vector primitives and deliberately rejects text, embedded images, and frames so they cannot silently disappear.
