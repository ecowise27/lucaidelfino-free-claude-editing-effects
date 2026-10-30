"""reelkit – kleine Video-Engine für die Reel-Skills.

Liest ein Video Frame für Frame (ffmpeg), legt Effekte darüber (Pillow + numpy)
und schreibt ein fertiges 9:16-Reel mit Originalton. Läuft überall, wo Python 3
und ffmpeg verfügbar sind; fehlt ffmpeg, wird imageio-ffmpeg nachgeladen.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"

W, H, FPS = 1080, 1920, 30

# Markenfarben (Standard: Luca). Überschreibbar per brand.json oder --brand.
BRAND = {
    "accent": "#5A3DF5",      # Lila
    "accent2": "#8B74FF",
    "green": "#20B67A",
    "ink": "#121214",
    "paper": "#FFFFFF",
    "soft": "#55555C",
    "highlight": "#5A3DF5",   # Hintergrund hinter Schlüsselwörtern
}


# --------------------------------------------------------------------------- ffmpeg

def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # type: ignore
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "imageio-ffmpeg"], check=True)
        import imageio_ffmpeg  # type: ignore
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(path: str) -> dict:
    """Dauer, Größe und Audio-Spur ermitteln (ohne ffprobe, nur über ffmpeg -i)."""
    out = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    dur = 0.0
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    if m:
        dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    has_audio = bool(re.search(r"Stream #.*Audio:", out))
    return {"duration": dur, "has_audio": has_audio}


# --------------------------------------------------------------------------- Marke & Schrift

def load_brand(path: str | None = None) -> dict:
    b = dict(BRAND)
    for p in [path, os.environ.get("REEL_BRAND"), str(Path.cwd() / "brand.json")]:
        if p and Path(p).is_file():
            b.update(json.loads(Path(p).read_text()))
            break
    return b


def rgba(hex_or_tuple, a: int = 255) -> tuple:
    if isinstance(hex_or_tuple, tuple):
        return hex_or_tuple if len(hex_or_tuple) == 4 else (*hex_or_tuple, a)
    h = hex_or_tuple.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


_font_cache: dict = {}


def font(size: int, weight: int = 800, serif: bool = False) -> ImageFont.FreeTypeFont:
    name = "InstrumentSerif-400-italic.ttf" if serif else f"DMSans-{min([500, 700, 800, 900], key=lambda w: abs(w - weight))}.ttf"
    key = (name, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(FONTS / name), size)
    return _font_cache[key]


def font_named(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Beliebige mitgelieferte Schrift, z. B. 'CourierPrime-Bold.ttf' oder 'InstrumentSerif-400.ttf'."""
    key = (name, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(FONTS / name), size)
    return _font_cache[key]


def shear(img: Image.Image, k: float = 0.18) -> Image.Image:
    """Kursiv-Effekt für Schriften ohne Italic-Schnitt."""
    extra = int(abs(k) * img.height)
    return img.transform((img.width + extra, img.height), Image.AFFINE, (1, k, -extra if k > 0 else 0, 0, 1, 0), resample=Image.BICUBIC)


_cmaps: dict = {}


def clean_text(txt: str, font_file: str = "DMSans-800.ttf") -> str:
    """Zeichen entfernen, die die Schrift nicht kennt (z. B. Emojis, ✓) – statt leerer Kästchen."""
    if font_file not in _cmaps:
        try:
            from fontTools.ttLib import TTFont
            _cmaps[font_file] = set(TTFont(str(FONTS / font_file)).getBestCmap())
        except Exception:
            _cmaps[font_file] = None
    cm = _cmaps[font_file]
    if not cm:
        return txt
    return "".join(c for c in txt if ord(c) in cm or c.isspace()).strip()


def text_size(txt: str, f: ImageFont.FreeTypeFont) -> tuple[int, int]:
    l, t, r, b = f.getbbox(txt)
    return r - l, b - t


# --------------------------------------------------------------------------- Animation

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x, s=1.70158):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def spring(x, damping=7.0, freq=2.2):
    """Federnde Bewegung von 0 nach 1 (für Pop-Ins)."""
    if x <= 0:
        return 0.0
    return 1 - math.exp(-damping * x) * math.cos(2 * math.pi * freq * x)


def window(t, t0, t1, fade_in=0.35, fade_out=0.3):
    """Fortschritt fürs Ein- (0..1) und Ausblenden (1..0) eines Elements."""
    if t < t0 or t > t1 + fade_out:
        return 0.0, 0.0
    pin = clamp((t - t0) / fade_in)
    pout = 1 - clamp((t - t1) / fade_out) if t > t1 else 1.0
    return pin, pout


# --------------------------------------------------------------------------- Zeichnen

def shadow_layer(size, box, radius, blur=40, opacity=110, offset=(0, 18)):
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0 + offset[0], y0 + offset[1], x1 + offset[0], y1 + offset[1]), radius, fill=(0, 0, 0, opacity))
    return lay.filter(ImageFilter.GaussianBlur(blur))


def card(w, h, radius=36, fill=(255, 255, 255, 255), border=None, shadow=True, pad=80):
    """Karte mit weichem Schatten als RGBA-Bild (inkl. Rand für den Schatten)."""
    size = (w + 2 * pad, h + 2 * pad)
    img = shadow_layer(size, (pad, pad, pad + w, pad + h), radius) if shadow else Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((pad, pad, pad + w, pad + h), radius, fill=fill, outline=border, width=2 if border else 0)
    return img, pad


def glass(frame: Image.Image, box, radius=40, blur=26, tint=(255, 255, 255, 38), border=(255, 255, 255, 90)):
    """Milchglas-Fläche: Hintergrund unter der Box weichzeichnen und aufhellen."""
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(frame.width, x1), min(frame.height, y1)
    if x1 <= x0 or y1 <= y0:
        return frame
    region = frame.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(blur)).convert("RGBA")
    over = Image.new("RGBA", region.size, tint)
    region = Image.alpha_composite(region, over)
    mask = Image.new("L", region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, region.width - 1, region.height - 1), radius, fill=255)
    frame.paste(region.convert(frame.mode), (x0, y0), mask)
    d = ImageDraw.Draw(frame, "RGBA")
    d.rounded_rectangle((x0, y0, x1 - 1, y1 - 1), radius, outline=border, width=2)
    return frame


def paste_scaled(frame: Image.Image, el: Image.Image, cx, cy, scale=1.0, alpha=1.0):
    """Element zentriert bei (cx, cy) mit Skalierung und Deckkraft einsetzen."""
    if alpha <= 0.01 or scale <= 0.01:
        return frame
    if abs(scale - 1) > 0.005:
        el = el.resize((max(1, int(el.width * scale)), max(1, int(el.height * scale))), Image.LANCZOS)
    if alpha < 0.999:
        a = el.getchannel("A").point(lambda v: int(v * alpha))
        el = el.copy()
        el.putalpha(a)
    frame.alpha_composite(el, (int(cx - el.width / 2), int(cy - el.height / 2))) if frame.mode == "RGBA" else frame.paste(el, (int(cx - el.width / 2), int(cy - el.height / 2)), el)
    return frame


def zoom_frame(frame: Image.Image, z: float, cx=0.5, cy=0.42) -> Image.Image:
    """Punch-in: ins Bild hineinzoomen (z=1 kein Zoom)."""
    if z <= 1.001:
        return frame
    w, h = frame.size
    cw, ch = w / z, h / z
    x0 = clamp(cx * w - cw / 2, 0, w - cw)
    y0 = clamp(cy * h - ch / 2, 0, h - ch)
    return frame.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((w, h), Image.LANCZOS)


# --------------------------------------------------------------------------- Render-Schleife

@dataclass
class Job:
    input: str
    output: str
    start: float = 0.0
    end: float | None = None
    crf: int = 18
    extra: dict = field(default_factory=dict)


def render(job: Job, effect, progress=True):
    """effect(frame: PIL.Image RGB, t: float, i: int) -> PIL.Image RGB"""
    ff = ffmpeg_bin()
    Path(job.output).parent.mkdir(parents=True, exist_ok=True)
    info = probe(job.input)
    end = job.end or info["duration"]
    dur = max(0.1, end - job.start)
    n = int(round(dur * FPS))
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"
    rd = subprocess.Popen([ff, "-v", "error", "-ss", str(job.start), "-t", str(dur), "-i", job.input,
                           "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = [ff, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if info["has_audio"]:
        enc += ["-ss", str(job.start), "-t", str(dur), "-i", job.input, "-map", "0:v", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"]
    enc += ["-c:v", "libx264", "-preset", "medium", "-crf", str(job.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", job.output]
    wr = subprocess.Popen(enc, stdin=subprocess.PIPE)
    fsize = W * H * 3
    i = 0
    while True:
        buf = rd.stdout.read(fsize)
        if len(buf) < fsize:
            break
        frame = Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1).copy()
        out = effect(frame, i / FPS, i)
        wr.stdin.write(out.convert("RGB").tobytes())
        i += 1
        if progress and i % 30 == 0:
            print(f"\r  Frame {i}/{n}", end="", flush=True)
    rd.wait()
    wr.stdin.close()
    wr.wait()
    if progress:
        print(f"\r  fertig: {job.output} ({i} Frames)")
    return job.output


def cli_common(ap):
    ap.add_argument("--input", "-i", required=True, help="Eingangsvideo")
    ap.add_argument("--output", "-o", required=True, help="Ausgabe .mp4")
    ap.add_argument("--start", type=float, default=0.0, help="Startzeit im Clip (Sek.)")
    ap.add_argument("--end", type=float, default=None, help="Endzeit im Clip (Sek.)")
    ap.add_argument("--brand", default=None, help="Pfad zu brand.json mit eigenen Farben")
    return ap
