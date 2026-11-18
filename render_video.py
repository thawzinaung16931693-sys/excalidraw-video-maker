#!/usr/bin/env python3
"""Render an SRT-timed illustrated video from Excalidrawlib and SVG assets."""
import argparse
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def timestamp(value):
    h, m, s, ms = map(int, re.split(r"[:,]", value))
    return h * 3600 + m * 60 + s + ms / 1000


def read_srt(path):
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip())
    cues = []
    for block in blocks:
        lines = block.splitlines()
        match = re.fullmatch(r"(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})", lines[1])
        if not match or len(lines) < 3:
            raise ValueError(f"Malformed SRT cue: {block[:80]}")
        start, end = map(timestamp, match.groups())
        if start >= end or (cues and start < cues[-1][1]):
            raise ValueError("SRT cue times overlap or reverse")
        cues.append((start, end, " ".join(lines[2:])))
    if not cues or cues[0][0] > .1:
        raise ValueError("SRT must begin at zero and contain at least one cue")
    return cues


def resolve(base, path):
    result = (base / path).resolve()
    if not result.is_file():
        raise FileNotFoundError(result)
    return result


def render_library_item(path, index, size, recolor=None):
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("libraryItems", data.get("library", []))
    item = items[index]
    elements = item["elements"] if isinstance(item, dict) else item
    bounds = []
    for element in elements:
        x, y = element.get("x", 0), element.get("y", 0)
        w, h = element.get("width", 0), element.get("height", 0)
        bounds.extend([(x, y), (x + w, y + h)])
        bounds.extend((x + p[0], y + p[1]) for p in element.get("points", []))
    if not bounds:
        raise ValueError(f"Empty library item {index} in {path}")
    x0, x1 = min(x for x, _ in bounds), max(x for x, _ in bounds)
    y0, y1 = min(y for _, y in bounds), max(y for _, y in bounds)
    scale = min((size[0] - 24) / max(x1 - x0, 1), (size[1] - 24) / max(y1 - y0, 1))
    def xy(x, y):
        return round((size[0] - (x1 - x0) * scale) / 2 + (x - x0) * scale), round((size[1] - (y1 - y0) * scale) / 2 + (y - y0) * scale)
    image = Image.new("RGBA", size)
    draw = ImageDraw.Draw(image)
    for e in elements:
        typ = e.get("type")
        x, y, w, h = (e.get(k, 0) for k in ("x", "y", "width", "height"))
        color = e.get("strokeColor", "#18334a")
        if recolor and color != "transparent":
            color = recolor
        stroke = None if color == "transparent" else color
        bg = e.get("backgroundColor", "transparent")
        fill = None if bg in ("transparent", "none", "#ff00") else bg
        width = max(2, round(e.get("strokeWidth", 1) * scale * .7))
        if typ == "rectangle":
            draw.rounded_rectangle((*xy(x, y), *xy(x + w, y + h)), radius=6, fill=fill, outline=stroke, width=width)
        elif typ == "ellipse":
            draw.ellipse((*xy(x, y), *xy(x + w, y + h)), fill=fill, outline=stroke, width=width)
        elif typ == "diamond":
            points = [xy(x+w/2,y),xy(x+w,y+h/2),xy(x+w/2,y+h),xy(x,y+h/2)]
            draw.polygon(points, fill=fill)
            if stroke: draw.line(points+[points[0]], fill=stroke, width=width, joint="curve")
        elif typ in ("line", "arrow", "freedraw", "draw"):
            points = [xy(x + p[0], y + p[1]) for p in e.get("points", [])]
            if len(points) > 1 and stroke:
                draw.line(points, fill=stroke, width=width, joint="curve")
        elif typ in ("text", "image", "frame"):
            raise ValueError(f"Library item {index} contains {typ}; export it from Excalidraw as SVG/PNG instead")
    return image


def load_image(base, spec, size, tempdir):
    if "library" in spec:
        return render_library_item(resolve(base, spec["library"]), spec["index"], size, spec.get("color"))
    path = resolve(base, spec["path"])
    if path.suffix.lower() == ".svg":
        png = Path(tempdir) / f"svg-{abs(hash((str(path), size)))}.png"
        subprocess.run(["inkscape", str(path), "--export-type=png", f"--export-width={size[0]}", f"--export-height={size[1]}", f"--export-filename={png}"], check=True, stdout=subprocess.DEVNULL)
        path = png
    return Image.open(path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)


def font_paths(config, base):
    regular = config.get("font_regular", "/usr/share/fonts/truetype/noto/NotoSansMyanmar-Regular.ttf")
    bold = config.get("font_bold", "/usr/share/fonts/truetype/noto/NotoSansMyanmar-Bold.ttf")
    def find(p):
        q = Path(p)
        return q if q.is_absolute() else resolve(base, p)
    return find(regular), find(bold), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')


def runs(text):
    result=[]
    for char in text:
        cp=ord(char)
        burmese=0x1000 <= cp <= 0x109f or 0xaa60 <= cp <= 0xaa7f or 0xa9e0 <= cp <= 0xa9ff
        if result and result[-1][0] == burmese:
            result[-1] = burmese, result[-1][1] + char
        else:
            result.append((burmese,char))
    return result


def mixed_width(draw, text, size, fonts, bold=True):
    return sum(draw.textlength(run,font=ImageFont.truetype(fonts[(0 if burmese else 2)+(1 if bold else 0)],size)) for burmese,run in runs(text))


def paint(draw, text, x, y, size, color, fonts, bold=True):
    for burmese,run in runs(text):
        font=ImageFont.truetype(fonts[(0 if burmese else 2)+(1 if bold else 0)],size)
        draw.text((x,y),run,font=font,fill=color,anchor="lt")
        x += draw.textlength(run,font=font)


def draw_text(draw, text, y, size, color, fonts, width, bold=True, x=None):
    while mixed_width(draw,text,size,fonts,bold) > width and size > 22:
        size -= 1
    if mixed_width(draw,text,size,fonts,bold) > width:
        raise ValueError(f"Text too wide; split it into shorter scenes: {text}")
    text_width = mixed_width(draw,text,size,fonts,bold)
    paint(draw,text,(720-text_width)/2 if x is None else x,y,size,color,fonts,bold)


def wrap(draw, text, size, fonts, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if current and mixed_width(draw,candidate,size,fonts) > max_width:
            lines.append(current); current = word
        else:
            current = candidate
    if current: lines.append(current)
    if any(mixed_width(draw,line,size,fonts) > max_width for line in lines):
        raise ValueError(f"Caption word too long: {text}")
    return lines


def frame(t, cue, scene, prepared, config, fonts):
    start, end, subtitle = cue
    bg, ink, accent = (config.get(k, default) for k, default in [("background", "#F7F5ED"),("ink", "#18334A"),("accent", "#26A7A1")])
    image = Image.new("RGBA", (720,1280), bg)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0,0,720,15), fill=accent)
    draw.rounded_rectangle((42,45,400,100), radius=22, fill=ink)
    draw_text(draw, config.get("brand", "VIDEO"), 59, 25, "#FFFFFF", fonts, 323, x=61)
    draw_text(draw, scene["title"], 165, 51, ink, fonts, 565)
    if scene.get("subtitle"):
        draw_text(draw, scene["subtitle"], 245, 34, accent, fonts, 590)
    if prepared.get("badge"):
        draw.ellipse((630,116,706,192),fill="#FFFFFF",outline="#D6E6E2",width=3)
        image.alpha_composite(prepared["badge"], (639,125))
    if prepared.get("icon"):
        icon = prepared["icon"]
        fade = min(1, max(0,(t-start)/.45), max(0,(end-t)/.45))
        if fade < 1:
            icon=icon.copy(); icon.putalpha(icon.getchannel("A").point(lambda v: round(v*fade)))
        image.alpha_composite(icon,(210,370+round(6*math.sin(t*2.4))))
    logos = prepared.get("logos", [])
    for n, (logo, label) in enumerate(logos[:2]):
        x = 80 if n == 0 else 390
        draw.rounded_rectangle((x,728,x+250,925),radius=25,fill="#FFFFFF",outline="#D6E6E2",width=3)
        image.alpha_composite(logo,(x+73,746))
        draw_text(draw,label,867,25,ink,fonts,220,x=x+20)
    for n, bullet in enumerate(scene.get("bullets", [])[:3]):
        y = 734+n*70 if not logos else 930+n*25
        draw_text(draw,bullet,y,25,ink,fonts,600,x=60)
    draw.rounded_rectangle((30,1000,690,1238),radius=30,fill="#FFFFFF",outline="#DCE8E4",width=2)
    lines = wrap(draw,subtitle,28,fonts,600)
    if len(lines) > 4: raise ValueError("Caption exceeds four lines; shorten or split its cue")
    for n,line in enumerate(lines): paint(draw,line,58,1040+n*42,28,ink,fonts)
    draw.rounded_rectangle((58,1208,662,1214),radius=3,fill="#E3EBE8")
    progress = min(1,max(0,(t-start)/(end-start)))
    draw.rounded_rectangle((58,1208,58+604*progress,1214),radius=3,fill=accent)
    return image.convert("RGB")


def duration(path):
    result = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],capture_output=True,text=True,check=True)
    return float(result.stdout.strip())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("storyboard",type=Path,help="JSON file; relative asset paths resolve from its directory")
    parser.add_argument("--preview",type=Path,help="Write a contact sheet instead of encoding video")
    parser.add_argument("--output",type=Path,help="MP4 output (required unless --preview)")
    args=parser.parse_args()
    if not args.preview and not args.output: parser.error("provide --output or --preview")
    base=args.storyboard.resolve().parent
    config=json.loads(args.storyboard.read_text(encoding="utf-8"))
    cues=read_srt(resolve(base,config["srt"]))
    scenes=config["scenes"]
    if len(scenes)!=len(cues): raise ValueError(f"Expected {len(cues)} scenes, got {len(scenes)}")
    fonts=font_paths(config,base)
    with tempfile.TemporaryDirectory() as temp:
        prepared=[]
        for scene in scenes:
            entry={}
            if scene.get("icon"): entry["icon"]=load_image(base,scene["icon"],(300,300),temp)
            if scene.get("badge"): entry["badge"]=load_image(base,scene["badge"],(58,58),temp)
            entry["logos"]=[(load_image(base,logo,(104,104),temp),logo.get("label","")) for logo in scene.get("logos",[])]
            prepared.append(entry)
        if args.preview:
            selected=list(range(min(4,len(cues))))
            contact=Image.new("RGB",(360*len(selected),640))
            for n,i in enumerate(selected):
                start,end,_=cues[i]
                contact.paste(frame((start+end)/2,cues[i],scenes[i],prepared[i],config,fonts).resize((360,640),Image.Resampling.LANCZOS),(n*360,0))
            args.preview.parent.mkdir(parents=True,exist_ok=True)
            contact.save(args.preview)
            print(args.preview)
            return
        voice=resolve(base,config["voice"])
        end=cues[-1][1]
        voice_length=duration(voice)
        if abs(end-voice_length) > .5:
            raise ValueError(f"SRT ends at {end:.3f}s but voice is {voice_length:.3f}s; retime SRT or edit audio without changing speaking rate")
        fps=int(config.get("fps",24))
        if not 12<=fps<=60: raise ValueError("fps must be between 12 and 60")
        temp_video=Path(temp)/"visuals.mp4"
        command=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pixel_format","rgb24","-video_size","720x1280","-framerate",str(fps),"-i","-","-an","-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast","-crf","20",str(temp_video)]
        proc=subprocess.Popen(command,stdin=subprocess.PIPE)
        try:
            idx=0
            for n in range(round(end*fps)):
                t=n/fps
                while idx<len(cues)-1 and t>=cues[idx][1]: idx+=1
                proc.stdin.write(frame(t,cues[idx],scenes[idx],prepared[idx],config,fonts).tobytes())
        finally:
            proc.stdin.close()
        if proc.wait()!=0: raise RuntimeError("Video encoding failed")
        args.output.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(temp_video),"-i",str(voice),"-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-b:a","160k","-t",str(end),"-movflags","+faststart",str(args.output)],check=True)
        print(args.output)


if __name__=="__main__": main()
