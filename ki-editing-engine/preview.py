"""Einzelnes Vorschaubild rendern – schnell prüfen, ob Position und Text passen, bevor das ganze Video läuft."""
from __future__ import annotations

import subprocess

from PIL import Image

from reelkit import FPS, H, W, ffmpeg_bin


def grab(path: str, t: float) -> Image.Image:
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
    raw = subprocess.run([ffmpeg_bin(), "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-vf", vf,
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return Image.frombuffer("RGB", (W, H), raw, "raw", "RGB", 0, 1).copy()


def still(path: str, t_abs: float, t_rel: float, run, out: str):
    frame = grab(path, t_abs)
    img = run(frame, t_rel, int(t_rel * FPS)).convert("RGB")
    if not out.lower().endswith((".png", ".jpg")):
        out = out.rsplit(".", 1)[0] + ".png"
    from pathlib import Path
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"Vorschau: {out}")
