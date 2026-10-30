"""Person freistellen (MediaPipe Selfie-Segmentierung) – für Effekte, die HINTER der Person liegen."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

MODELS = Path(__file__).resolve().parent / "models"


def ensure_mediapipe():
    try:
        import mediapipe  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "mediapipe"], check=True)


class Segmenter:
    """mask(frame, t) -> Graustufen-Maske (255 = Person), zeitlich geglättet gegen Flackern."""

    def __init__(self, quality: str = "fast", smooth: float = 0.55, feather: int = 3):
        ensure_mediapipe()
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        self.mp = mp
        model = MODELS / ("selfie_multiclass.tflite" if quality == "fine" and (MODELS / "selfie_multiclass.tflite").exists() else "selfie_segmenter.tflite")
        self.multiclass = "multiclass" in model.name
        opts = vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path=str(model)),
                                            running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True)
        self.seg = vision.ImageSegmenter.create_from_options(opts)
        self.prev = None
        self.smooth, self.feather = smooth, feather
        self.last_ts = -1

    def mask(self, frame: Image.Image, t: float) -> Image.Image:
        ts = max(self.last_ts + 1, int(t * 1000))
        self.last_ts = ts
        small = frame.convert("RGB").resize((frame.width // 2, frame.height // 2))
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.asarray(small))
        res = self.seg.segment_for_video(img, ts)
        if self.multiclass:  # Klasse 0 = Hintergrund → Person = 1 - Hintergrund
            m = 1.0 - res.confidence_masks[0].numpy_view()
        else:
            m = res.confidence_masks[0].numpy_view()
        m = np.squeeze(m).astype(np.float32)
        if self.prev is not None and self.prev.shape == m.shape:
            m = self.smooth * self.prev + (1 - self.smooth) * m
        self.prev = m
        m = np.clip((m - 0.35) / 0.3, 0, 1)  # Kante schärfen
        out = Image.fromarray((m * 255).astype("uint8")).resize(frame.size, Image.BILINEAR)
        return out.filter(ImageFilter.GaussianBlur(self.feather)) if self.feather else out
