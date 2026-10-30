"""Effekte Runde 3: Vogue-Cover, Hollywood-KI-Scan, Sticker v2, Instagram-iPhone, Dolly-Zoom, Doodle-Burst,
Polaroid-Dump, VHS-Rewind, Bento-Grid. Wird aus effects.py nachgeladen."""
from __future__ import annotations

import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from effects import Effect, clean_text, text_img
from effects_pro import additive, app_logo, cutout, find_coeffs, head_box, person_mask
from reelkit import (FONTS, FPS, H, W, clamp, ease_in_out, ease_out_back, ease_out_cubic, font, font_named, paste_scaled,
                     rgba, spring, text_size, window, zoom_frame)

_vf: dict = {}


def bodoni(size, weight=500, italic=False):
    key = (size, weight, italic)
    if key not in _vf:
        f = ImageFont.truetype(str(FONTS / ("BodoniModa-Italic.ttf" if italic else "BodoniModa.ttf")), size)
        try:
            f.set_variation_by_axes([weight, 96])
        except Exception:
            pass
        _vf[key] = f
    return _vf[key]


def marker(size):
    return font_named("PermanentMarker-Regular.ttf", size)


def alpha_mul(img, a):
    if a >= 0.999:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


# --------------------------------------------------------------------------- Gesichtsnetz (Face Mesh)

_FM = {"lm": None, "t": None, "pts": None}


def face_points(frame, t):
    """478 Gesichtspunkte in Pixeln (oder None)."""
    if _FM["t"] == t:
        return _FM["pts"]
    if _FM["lm"] is None:
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(Path(__file__).resolve().parent / "models" / "face_landmarker.task")),
                                            running_mode=vision.RunningMode.VIDEO, num_faces=1)
        _FM["lm"] = (vision.FaceLandmarker.create_from_options(opts), mp, 0)
    lm, mp, last = _FM["lm"]
    ts = max(last + 1, int(t * 1000))
    _FM["lm"] = (lm, mp, ts)
    res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(frame.convert("RGB"))), ts)
    pts = None
    if res.face_landmarks:
        pts = np.array([(p.x * W, p.y * H) for p in res.face_landmarks[0]], np.float32)
    _FM.update(t=t, pts=pts)
    return pts


def tessellation():
    from mediapipe.tasks.python.vision import FaceLandmarksConnections as F
    return [(c.start, c.end) for c in F.FACE_LANDMARKS_TESSELATION]


# =========================================================================== Vogue-Cover

class VogueCover(Effect):
    """Modemagazin-Cover: Blitz, edle Bodoni-Titelzeile HINTER dem Kopf, Coverzeilen, Fashion-Farblook."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.9, 0.4)
        if pin <= 0:
            return frame
        rel = t - self.at
        z = 1 + 0.04 * ease_out_cubic(clamp(rel / 3))
        fr = zoom_frame(frame, z, cy=0.42)
        m = person_mask(frame, t)
        mz = zoom_frame(m.convert("RGB"), z, cy=0.42).convert("L")
        # Fashion-Look: mehr Kontrast, Hintergrund leicht entsättigt und dunkler
        g = np.asarray(fr, np.float32) / 255
        g = np.clip((g - 0.5) * 1.12 + 0.5 + 0.02, 0, 1)
        gray = g.mean(axis=2, keepdims=True)
        pm = np.asarray(mz, np.float32)[..., None] / 255
        bg = (gray * 0.55 + g * 0.45) * 0.78
        g = g * pm + bg * (1 - pm)
        graded = Image.fromarray((g * 255).astype("uint8"))
        out = Image.blend(fr, graded, clamp(rel * 3) * pout).convert("RGBA")
        col = rgba(self.cfg.get("titelfarbe", "#FFFFFF"))
        title = self.cfg.get("titel", "LUCA").upper()
        size = 420
        f = bodoni(size, 600)
        while f.getlength(title) > W * 0.94 and size > 120:
            size -= 10
            f = bodoni(size, 600)
        if not hasattr(self, "_ty"):
            hb = head_box(mz)
            l_, t_, r_, b_ = f.getbbox(title)
            self._th = b_ - t_
            self._ty = max(150, hb[1] + (hb[3] - hb[1]) * 0.18 - self._th)   # Unterkante des Titels hinter der Stirn
        tp = ease_out_cubic(clamp((rel - 0.2) / 0.9)) * pout
        track = int(40 * (1 - tp))                    # Buchstaben laufen zusammen
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        widths = [f.getlength(c) for c in title]
        total = sum(widths) + track * (len(title) - 1)
        x = (W - total) / 2
        for c, wd in zip(title, widths):
            d.text((x, self._ty), c, font=f, fill=col[:3] + (int(255 * tp),), anchor="la")
            x += wd + track
        if tp < 0.95:
            lay = lay.filter(ImageFilter.GaussianBlur(6 * (1 - tp)))
        out = Image.alpha_composite(out, lay)
        out.paste(fr.convert("RGBA"), (0, 0), mz)         # Kopf vor dem Titel
        out.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)))
        d = ImageDraw.Draw(out)
        small = font(24, 800)
        top = self.cfg.get("kopfzeile", "DEUTSCHLAND  ·  NOVEMBER 2026  ·  € 7,50")
        a1 = int(255 * ease_out_cubic(clamp((rel - 0.5) / 0.5)) * pout)
        d.text((W / 2, 92), " ".join(top), font=font(20, 800), fill=(255, 255, 255, a1), anchor="mm")
        # Coverzeilen links
        lines = self.cfg.get("zeilen", [["DAS KI-ISSUE", "k"], ["Die neue Ära", "h"], ["der Creator", "h"], ["Wie Claude Reels schneidet", "s"]])
        y = H * float(self.cfg.get("zeilen_y", 0.585))
        for k, (txt, typ) in enumerate(lines):
            a = ease_out_cubic(clamp((rel - 0.7 - 0.18 * k) / 0.45)) * pout
            if a <= 0:
                continue
            if typ == "k":
                fnt, fill = font(26, 900), rgba(self.cfg.get("akzent", "#E8C27A"))
                txt = " ".join(txt)
            elif typ == "h":
                fnt, fill = bodoni(76, 500, italic=True), (255, 255, 255, 255)
            else:
                fnt, fill = font(30, 700), (235, 235, 235, 255)
            el = text_img(clean_text(txt), fnt, fill=fill, shadow_alpha=150, pad=8)
            out.alpha_composite(alpha_mul(el, a), (int(56 - (1 - a) * 30), int(y)))
            y += el.height - (14 if typ == "h" else 6)
        # Name unten rechts
        name = self.cfg.get("name", "LUCA DELFINO")
        a = ease_out_cubic(clamp((rel - 1.3) / 0.5)) * pout
        if a > 0:
            el = text_img(name, bodoni(64, 600), shadow_alpha=170, pad=8)
            out.alpha_composite(alpha_mul(el, a), (int(W - el.width - 50), int(H * 0.78)))
            sub = text_img(self.cfg.get("unterzeile", "über KI, Kontrolle & Kreativität"), font(28, 700), shadow_alpha=170, pad=6)
            out.alpha_composite(alpha_mul(sub, a), (int(W - sub.width - 52), int(H * 0.78 + el.height - 14)))
        flash = 1 - clamp(rel / 0.18)
        if flash > 0:
            out = Image.blend(out, Image.new("RGBA", (W, H), (255, 255, 255, 255)), flash * 0.85)
        return out


# =========================================================================== Hollywood-KI-Scan

class AIScanHollywood(Effect):
    """Sci-Fi-Gesichtsscan wie im Kino: leuchtendes Gesichtsnetz, rotierende Zielringe, Hologramm-Datenpanels, Lock-on."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.25, 0.35)
        if pin <= 0:
            return frame
        rel, dur = t - self.at, max(1.5, self.until - self.at)
        acc = np.array(rgba(self.cfg.get("color", "#38E1FF"))[:3], np.float32)
        pts = face_points(frame, t)
        # Kino-Grading: kühl, kontrastreich, Vignette
        g = np.asarray(frame.convert("RGB"), np.float32) / 255
        g = np.clip((g - 0.5) * 1.15 + 0.5, 0, 1)
        g = g * np.array([0.82, 0.95, 1.08], np.float32)
        Y, X = np.ogrid[0:H, 0:W]
        vig = 1 - 0.6 * np.clip(np.hypot((X - W / 2) / (W * 0.7), (Y - H * 0.42) / (H * 0.62)), 0, 1)[..., None] ** 2
        g = np.clip(g * vig, 0, 1)
        base = Image.blend(frame.convert("RGB"), Image.fromarray((g * 255).astype("uint8")), clamp(rel * 4) * pout)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        A = lambda a: tuple(int(c) for c in acc) + (int(255 * clamp(a) * pout),)
        cx, cy, rad = W / 2, H * 0.36, W * 0.3
        if pts is not None:
            cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
            rad = max(pts[:, 0].max() - pts[:, 0].min(), pts[:, 1].max() - pts[:, 1].min()) * 0.62
            scan_y = pts[:, 1].min() + (pts[:, 1].max() - pts[:, 1].min() + 40) * ease_in_out(clamp(rel / (dur * 0.35)))
            mesh_a = clamp((rel - 0.1) * 3) * (1 - clamp((rel - dur * 0.7) / 0.4) * 0.6)
            flick = 0.75 + 0.25 * math.sin(t * 40)
            if not hasattr(self, "_tess"):
                self._tess = tessellation()
            for a_, b_ in self._tess:
                p, q = pts[a_], pts[b_]
                if p[1] > scan_y and q[1] > scan_y:
                    continue
                d.line((p[0], p[1], q[0], q[1]), fill=A(0.62 * mesh_a * flick), width=2)
            for k in range(0, len(pts), 3):
                x, y = pts[k]
                if y <= scan_y:
                    d.ellipse((x - 2.6, y - 2.6, x + 2.6, y + 2.6), fill=A(1.0 * mesh_a))
            if rel < dur * 0.4:
                d.line((cx - rad * 1.2, scan_y, cx + rad * 1.2, scan_y), fill=A(0.95), width=3)
        # rotierende Zielringe
        rp = ease_out_cubic(clamp(rel / 0.6))
        R1, R2 = rad * (1.9 - 0.6 * rp), rad * (1.6 - 0.45 * rp)
        lock = clamp((rel - dur * 0.55) / 0.2)
        spin = t * (90 if lock < 1 else 20)
        for k in range(4):
            st = spin + k * 90
            d.arc((cx - R1, cy - R1, cx + R1, cy + R1), st, st + 55, fill=A(0.85), width=4)
        for k in range(3):
            st = -spin * 1.4 + k * 120
            d.arc((cx - R2, cy - R2, cx + R2, cy + R2), st, st + 70, fill=A(0.55), width=2)
        for k in range(72):
            an = math.radians(k * 5 + spin * 0.3)
            r0, r1 = R1 + 10, R1 + (24 if k % 6 == 0 else 16)
            d.line((cx + r0 * math.cos(an), cy + r0 * math.sin(an), cx + r1 * math.cos(an), cy + r1 * math.sin(an)), fill=A(0.5), width=2)
        # Fadenkreuz-Linien zu den Rändern
        for (x0, y0, x1, y1) in [(0, cy, cx - R1 - 30, cy), (cx + R1 + 30, cy, W, cy), (cx, 0, cx, cy - R1 - 30)]:
            d.line((x0, y0, x1, y1), fill=A(0.35), width=2)
        # Hologramm-Panels
        mono = lambda s: font_named("CourierPrime-Bold.ttf", s)
        panels = [
            (40, H * 0.70, "BIOMETRIE", [("PULS", 72, " BPM"), ("FOKUS", 97, " %"), ("KI-AFFINITÄT", 99, " %")]),
            (W - 400, H * 0.70, "PROFIL", [("CREATOR-LEVEL", 9, "/10"), ("REICHWEITE", 3, " MIO"), ("STATUS", None, "AKTIV")]),
        ]
        for k, (px, py, title, rows) in enumerate(panels):
            pa = ease_out_cubic(clamp((rel - 0.5 - 0.2 * k) / 0.4))
            if pa <= 0:
                continue
            pw, ph = 360, 250
            d.rectangle((px, py, px + pw, py + ph), fill=(4, 18, 26, int(150 * pa * pout)), outline=A(0.7 * pa), width=2)
            d.line((px, py + 44, px + pw * pa, py + 44), fill=A(0.7 * pa), width=2)
            d.text((px + 14, py + 10), title, font=mono(26), fill=A(pa))
            for j, (lab, val, unit) in enumerate(rows):
                ry = py + 60 + j * 62
                d.text((px + 14, ry), lab, font=mono(20), fill=A(0.7 * pa))
                if val is None:
                    txt = unit
                else:
                    txt = f"{int(val * clamp((rel - 0.6 - 0.15 * j) / 0.8))}{unit}"
                d.text((px + pw - 14, ry), txt, font=mono(24), fill=(235, 252, 255, int(255 * pa * pout)), anchor="ra")
                bw = (pw - 28) * clamp((rel - 0.6 - 0.15 * j) / 0.8) * (0.4 + 0.6 * ((val or 100) / 100 if (val or 100) <= 100 else 1))
                d.rectangle((px + 14, ry + 32, px + 14 + bw, ry + 38), fill=A(0.8 * pa))
        # Lock-on Banner
        if lock > 0:
            name = self.cfg.get("name", "LUCA DELFINO")
            ba = ease_out_cubic(lock)
            bw_ = 760
            by = cy + R1 + 60
            d.rectangle((W / 2 - bw_ / 2, by, W / 2 + bw_ / 2, by + 120), fill=(4, 18, 26, int(190 * ba * pout)), outline=A(ba), width=3)
            d.text((W / 2, by + 34), "IDENTITÄT BESTÄTIGT", font=mono(30), fill=A(ba), anchor="mm")
            d.text((W / 2, by + 82), " ".join(name), font=font(40, 900), fill=(255, 255, 255, int(255 * ba * pout)), anchor="mm")
        glow = lay.filter(ImageFilter.GaussianBlur(8))
        out = Image.alpha_composite(base.convert("RGBA"), glow)
        out = Image.alpha_composite(out, lay)
        # Scanlines + leichte RGB-Verschiebung
        a = np.asarray(out.convert("RGB"), np.float32)
        a[::3] *= 0.9
        s = 3
        a[..., 0] = np.roll(a[..., 0], s, axis=1)
        a[..., 2] = np.roll(a[..., 2], -s, axis=1)
        out = Image.fromarray(np.clip(a, 0, 255).astype("uint8"))
        fl = clamp(1 - abs(rel - dur * 0.55) / 0.07) * 0.6
        if fl > 0:
            out = Image.blend(out, Image.new("RGB", (W, H), tuple(int(c) for c in acc)), fl)
        if int(t * 30) % 23 == 0:   # seltenes Glitch-Flackern
            a = np.asarray(out).copy()
            y0 = int((t * 997) % (H - 80))
            a[y0:y0 + 60] = np.roll(a[y0:y0 + 60], 40, axis=1)
            out = Image.fromarray(a)
        return out


# =========================================================================== Freeze-Sticker v2

class FreezeStickerPro(Effect):
    """Standbild im Druck-Look (Halbton), Person als glänzender Sticker mit dickem Rand, Marker-Beschriftung, Kritzel-Pfeil, Sternchen und Stempel."""

    def covers(self, t):
        return self.at <= t <= self.until

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            self.__dict__.pop("_fz", None)
            return frame
        if not hasattr(self, "_fz"):
            mk = person_mask(frame, t)
            half = mk.resize((W // 2, H // 2))
            stroke = half.filter(ImageFilter.MaxFilter(int(self.cfg.get("rand", 19)) | 1)).resize((W, H), Image.BILINEAR)
            stroke = stroke.point(lambda v: 255 if v > 90 else 0).filter(ImageFilter.GaussianBlur(1.3))
            g = ImageOps.grayscale(frame).filter(ImageFilter.GaussianBlur(2))
            # Halbton-Raster
            arr = np.asarray(g.resize((W // 10, H // 10)), np.float32) / 255
            ht = Image.new("L", (W, H), 236)
            hd = ImageDraw.Draw(ht)
            for yy in range(arr.shape[0]):
                for xx in range(arr.shape[1]):
                    r = (1 - arr[yy, xx]) * 6.2
                    if r > 0.6:
                        cx_, cy_ = xx * 10 + 5 + (5 if yy % 2 else 0), yy * 10 + 5
                        hd.ellipse((cx_ - r, cy_ - r, cx_ + r, cy_ + r), fill=40)
            paper = ImageOps.colorize(ht, rgba(self.cfg.get("druckfarbe", "#2B2140"))[:3], (245, 238, 225))
            sticker = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sticker.paste(Image.new("RGBA", (W, H), (255, 255, 255, 255)), (0, 0), stroke)
            sticker.alpha_composite(cutout(frame, mk))
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shadow.paste(Image.new("RGBA", (W, H), (0, 0, 0, 170)), (18, 30), stroke)
            self._fz = (frame.copy(), paper, sticker, shadow.filter(ImageFilter.GaussianBlur(20)), stroke, head_box(mk))
        orig, paper, sticker, shadow, stroke, hb = self._fz
        rel = t - self.at
        p = ease_out_cubic(clamp(rel / 0.3))
        out = Image.blend(orig.convert("RGB"), paper, p).convert("RGBA")
        # Glanzstreifen über den Sticker
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gx = -300 + (W + 600) * clamp((rel - 0.35) / 0.7)
        ImageDraw.Draw(sh).polygon([(gx, 0), (gx + 120, 0), (gx - 380, H), (gx - 500, H)], fill=(255, 255, 255, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        sh.putalpha(ImageChops.multiply(sh.getchannel("A"), sticker.getchannel("A")))
        lay = Image.alpha_composite(shadow, sticker)
        lay = Image.alpha_composite(lay, sh)
        s = 1 + 0.07 * spring(clamp(rel / 0.6), 6, 1.5)
        rot = -3.5 * ease_out_back(clamp(rel / 0.5))
        lay = lay.rotate(rot, resample=Image.BICUBIC, center=(W / 2, H * 0.7))
        lay = lay.resize((int(W * s), int(H * s)), Image.LANCZOS)
        lay = lay.crop(((lay.width - W) // 2, int((lay.height - H) * 0.75), (lay.width - W) // 2 + W, int((lay.height - H) * 0.75) + H))
        out.alpha_composite(lay)
        d = ImageDraw.Draw(out)
        ink = rgba(self.cfg.get("color", "#FFD84D"))
        # Marker-Beschriftung
        label = self.cfg.get("label", "Ich vor Claude")
        side = self.cfg.get("seite", "links")
        la = ease_out_cubic(clamp((rel - 0.25) / 0.3))
        if label and la > 0:
            el = text_img(clean_text(label, "PermanentMarker-Regular.ttf"), marker(int(self.cfg.get("size", 82))), fill=ink, shadow_alpha=200, pad=16)
            el = el.rotate(6 if side == "links" else -6, resample=Image.BICUBIC, expand=True)
            lx = W * (0.30 if side == "links" else 0.70)
            ly = max(150, hb[1] - 70)
            paste_scaled(out, el, lx, ly, 0.8 + 0.2 * la, la)
            # wackeliger Pfeil (zeichnet sich)
            ax0, ay0 = lx + (60 if side == "links" else -60), ly + 60
            tx, ty = (hb[0] + 10, hb[1] + (hb[3] - hb[1]) * 0.45) if side == "links" else (hb[2] - 10, hb[1] + (hb[3] - hb[1]) * 0.45)
            rng = np.random.default_rng(int(t * FPS) // 3)
            n = int(24 * clamp((rel - 0.35) / 0.4))
            pts = []
            for i in range(n + 1):
                q = i / 24
                bx = ax0 + (tx - ax0) * q + rng.normal(0, 1.5)
                by = ay0 + (ty - ay0) * q - math.sin(q * math.pi) * 90 + rng.normal(0, 1.5)
                pts.append((bx, by))
            if len(pts) > 1:
                d.line(pts, fill=ink, width=10, joint="curve")
                if n >= 24:
                    ex, ey = pts[-1]
                    px_, py_ = pts[-4]
                    an = math.atan2(ey - py_, ex - px_)
                    for da in (2.5, -2.5):
                        d.line((ex, ey, ex + 46 * math.cos(an + da), ey + 46 * math.sin(an + da)), fill=ink, width=10)
        # Sternchen-Kritzel
        sa = clamp((rel - 0.5) / 0.3)
        if sa > 0:
            rng = np.random.default_rng(int(t * FPS) // 3)
            for (sx, sy, r) in [(hb[2] + 40, hb[1] + 10, 34), (hb[2] + 90, hb[1] + 90, 22), (hb[0] - 50, hb[3] - 20, 26)]:
                r *= sa
                for an in (0, math.pi / 2):
                    j = rng.normal(0, 1.2, 4)
                    d.line((sx - r * math.cos(an) + j[0], sy - r * math.sin(an) + j[1], sx + r * math.cos(an) + j[2], sy + r * math.sin(an) + j[3]), fill=(255, 255, 255, 255), width=7)
        # Stempel
        stamp = self.cfg.get("stempel", "VORHER")
        st_a = clamp((rel - 0.6) / 0.15)
        if stamp and st_a > 0:
            fs = font(54, 900)
            tw_, th_ = text_size(stamp, fs)
            el = Image.new("RGBA", (tw_ + 60, th_ + 50), (0, 0, 0, 0))
            ed = ImageDraw.Draw(el)
            red = rgba(self.cfg.get("stempelfarbe", "#E3242B"))
            ed.rectangle((4, 4, el.width - 5, el.height - 5), outline=red, width=7)
            l_, t_, _, _ = fs.getbbox(stamp)
            ed.text((30 - l_, 25 - t_), stamp, font=fs, fill=red)
            el = el.rotate(-12, resample=Image.BICUBIC, expand=True)
            paste_scaled(out, el, W * (0.72 if side == "links" else 0.28), H * 0.83, 1.6 - 0.6 * ease_out_cubic(st_a), st_a)
        flash = 1 - clamp(rel / 0.12)
        if flash > 0:
            out = Image.blend(out, Image.new("RGBA", (W, H), (255, 255, 255, 255)), flash * 0.8)
        return out


# =========================================================================== Instagram-iPhone (Handy-Portal v2)

def _heart(d, cx, cy, s, fill=None, outline=None, width=5):
    pts = []
    for k in range(60):
        a = k / 60 * 2 * math.pi
        x = 16 * math.sin(a) ** 3
        y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((cx + x * s / 17, cy + y * s / 17))
    if fill:
        d.polygon(pts, fill=fill)
    if outline:
        d.line(pts + [pts[0]], fill=outline, width=width, joint="curve")


def insta_ui(screen: Image.Image, t, cfg, avatar, liked_at=None):
    """Instagram-Reels-Oberfläche über ein 9:16-Bild legen (eigene Zeichnung, keine Original-Grafiken)."""
    w, h = screen.size
    k = w / 1080
    s = screen.convert("RGBA")
    grad = Image.linear_gradient("L").resize((w, h))
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    shade.putalpha(grad.point(lambda v: int(max(0, v - 150) * 1.4)))
    s = Image.alpha_composite(s, shade)
    d = ImageDraw.Draw(s)
    white = (255, 255, 255, 255)
    F = lambda sz, wt=800: font(int(sz * k), wt)
    # Statusleiste
    d.text((70 * k, 58 * k), "9:41", font=F(40), fill=white, anchor="lm")
    bx = w - 70 * k
    d.rounded_rectangle((bx - 62 * k, 44 * k, bx, 74 * k), 8 * k, outline=white, width=int(3 * k) or 1)
    d.rectangle((bx - 58 * k, 48 * k, bx - 14 * k, 70 * k), fill=white)
    for i in range(4):
        d.rectangle((bx - 170 * k + i * 16 * k, 70 * k - (i + 1) * 7 * k, bx - 160 * k + i * 16 * k, 70 * k), fill=white)
    # Kopfzeile
    d.text((60 * k, 160 * k), "Reels", font=F(58, 900), fill=white, anchor="lm")
    d.rounded_rectangle((w - 120 * k, 130 * k, w - 64 * k, 186 * k), 12 * k, outline=white, width=int(5 * k) or 1)
    d.ellipse((w - 104 * k, 146 * k, w - 80 * k, 170 * k), outline=white, width=int(5 * k) or 1)
    # rechte Leiste
    rx = w - 92 * k
    ry = h * 0.52
    liked = liked_at is not None and t >= liked_at
    _heart(d, rx, ry, 46 * k, fill=(255, 48, 64, 255) if liked else None, outline=None if liked else white, width=int(6 * k) or 1)
    d.text((rx, ry + 62 * k), cfg.get("likes", "48,2K"), font=F(30), fill=white, anchor="mm")
    cy = ry + 170 * k
    d.ellipse((rx - 40 * k, cy - 40 * k, rx + 40 * k, cy + 36 * k), outline=white, width=int(6 * k) or 1)
    d.polygon([(rx - 30 * k, cy + 22 * k), (rx - 44 * k, cy + 46 * k), (rx - 12 * k, cy + 34 * k)], fill=white)
    d.text((rx, cy + 76 * k), cfg.get("kommentare", "1.204"), font=F(30), fill=white, anchor="mm")
    py = cy + 180 * k
    d.polygon([(rx - 42 * k, py - 30 * k), (rx + 44 * k, py - 40 * k), (rx + 4 * k, py + 40 * k), (rx - 6 * k, py + 2 * k)], outline=white, width=int(6 * k) or 1)
    d.text((rx, py + 80 * k), cfg.get("geteilt", "9.876"), font=F(30), fill=white, anchor="mm")
    for i in range(3):
        d.ellipse((rx - 5 * k + (i - 1) * 18 * k, py + 160 * k, rx + 5 * k + (i - 1) * 18 * k, py + 170 * k), fill=white)
    # Profil unten links
    by = h - 330 * k
    if avatar is not None:
        av = avatar.resize((int(84 * k), int(84 * k)))
        m = Image.new("L", av.size, 0)
        ImageDraw.Draw(m).ellipse((0, 0, av.width - 1, av.height - 1), fill=255)
        s.paste(av, (int(50 * k), int(by - 42 * k)), m)
    d.text((150 * k, by), cfg.get("name", "lucaidelfino"), font=F(38, 800), fill=white, anchor="lm")
    nw = F(38, 800).getlength(cfg.get("name", "lucaidelfino"))
    fx = 150 * k + nw + 26 * k
    d.rounded_rectangle((fx, by - 30 * k, fx + 150 * k, by + 30 * k), 14 * k, outline=white, width=int(4 * k) or 1)
    d.text((fx + 75 * k, by), "Folgen", font=F(30), fill=white, anchor="mm")
    d.text((50 * k, by + 80 * k), clean_text(cfg.get("caption", "So schneide ich meine Reels mit Claude")), font=F(34, 500), fill=white, anchor="lm")
    d.text((50 * k, by + 140 * k), "Originalton · " + cfg.get("name", "lucaidelfino"), font=F(30, 500), fill=(230, 230, 230, 255), anchor="lm")
    # Tab-Leiste
    ty = h - 90 * k
    d.rectangle((0, h - 160 * k, w, h), fill=(0, 0, 0, 255))
    xs = [w * (i + 0.5) / 5 for i in range(5)]
    d.polygon([(xs[0] - 30 * k, ty), (xs[0], ty - 28 * k), (xs[0] + 30 * k, ty), (xs[0] + 30 * k, ty + 30 * k), (xs[0] - 30 * k, ty + 30 * k)], outline=white, width=int(5 * k) or 1)
    d.ellipse((xs[1] - 24 * k, ty - 24 * k, xs[1] + 18 * k, ty + 18 * k), outline=white, width=int(5 * k) or 1)
    d.line((xs[1] + 12 * k, ty + 12 * k, xs[1] + 30 * k, ty + 30 * k), fill=white, width=int(5 * k) or 1)
    d.rounded_rectangle((xs[2] - 30 * k, ty - 30 * k, xs[2] + 30 * k, ty + 30 * k), 12 * k, outline=white, width=int(5 * k) or 1)
    d.line((xs[2], ty - 16 * k, xs[2], ty + 16 * k), fill=white, width=int(5 * k) or 1)
    d.line((xs[2] - 16 * k, ty, xs[2] + 16 * k, ty), fill=white, width=int(5 * k) or 1)
    d.rounded_rectangle((xs[3] - 30 * k, ty - 30 * k, xs[3] + 30 * k, ty + 30 * k), 12 * k, fill=white)
    d.polygon([(xs[3] - 8 * k, ty - 12 * k), (xs[3] + 14 * k, ty), (xs[3] - 8 * k, ty + 12 * k)], fill=(0, 0, 0, 255))
    if avatar is not None:
        av = avatar.resize((int(60 * k), int(60 * k)))
        m = Image.new("L", av.size, 0)
        ImageDraw.Draw(m).ellipse((0, 0, av.width - 1, av.height - 1), fill=255)
        s.paste(av, (int(xs[4] - 30 * k), int(ty - 30 * k)), m)
    # Doppeltipp-Herz
    if liked_at is not None and 0 <= t - liked_at < 0.9:
        q = t - liked_at
        sc = ease_out_back(clamp(q / 0.25)) * (1 if q < 0.6 else 1 - (q - 0.6) / 0.3)
        hl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        _heart(ImageDraw.Draw(hl), w / 2, h * 0.45, 200 * k * max(0.01, sc), fill=(255, 255, 255, 235))
        s = Image.alpha_composite(s, hl)
    return s


class InstaPhone(Effect):
    """Das Video wird zu einem Instagram-Reel auf einem iPhone (Titanrahmen, Dynamic Island), schwebt in 3D und zoomt zurück."""

    def covers(self, t):
        return self.at + 0.2 <= t <= self.until - 0.2

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        tr = float(self.cfg.get("uebergang", 0.55))
        s = ease_in_out(clamp((t - self.at) / tr)) * (1 - ease_in_out(clamp((t - (self.until - tr)) / tr)))
        if s < 0.003:
            return frame
        if not hasattr(self, "_avatar"):
            hb = head_box(person_mask(frame, t))
            c = ((hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2)
            r = (hb[2] - hb[0]) * 0.75
            self._avatar = frame.crop((int(c[0] - r), int(c[1] - r), int(c[0] + r), int(c[1] + r))).convert("RGB")
        k = 1 - 0.38 * s
        sw_, sh_ = int(W * k), int(H * k)
        screen = insta_ui(frame.resize((sw_, sh_), Image.LANCZOS), t, self.cfg, self._avatar,
                          liked_at=self.at + float(self.cfg.get("like_nach", 1.4)) if s > 0.9 or t > self.at + 1 else None)
        screen = Image.blend(frame.resize((sw_, sh_)).convert("RGBA"), screen, clamp(s * 1.4))
        rad = int(sw_ * 0.12 * s) + 1
        bez = int(16 * s) + 1
        rim = int(10 * s) + 1
        pw, ph = sw_ + 2 * (bez + rim), sh_ + 2 * (bez + rim)
        ph_img = Image.new("RGBA", (pw + 30, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(ph_img)
        # Seitentasten
        for (x0, y0, y1) in [(0, ph * 0.18, ph * 0.23), (0, ph * 0.27, ph * 0.35), (0, ph * 0.37, ph * 0.45)]:
            d.rounded_rectangle((x0 + 6, y0, x0 + 18, y1), 5, fill=(150, 150, 156, 255))
        d.rounded_rectangle((pw + 12, ph * 0.28, pw + 24, ph * 0.40), 5, fill=(150, 150, 156, 255))
        d.rounded_rectangle((pw + 12, ph * 0.55, pw + 22, ph * 0.62), 4, fill=(120, 120, 126, 255))
        # Titanrahmen mit Verlauf
        frame_g = Image.linear_gradient("L").rotate(90).resize((pw, ph)).point(lambda v: int(150 + 70 * math.sin(v / 255 * math.pi)))
        rimimg = Image.merge("RGBA", [frame_g, frame_g, frame_g.point(lambda v: min(255, v + 6)), Image.new("L", (pw, ph), 255)])
        rm = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(rm).rounded_rectangle((0, 0, pw - 1, ph - 1), rad + bez + rim, fill=255)
        ph_img.paste(rimimg, (15, 0), rm)
        d.rounded_rectangle((15 + rim, rim, 15 + pw - rim - 1, ph - rim - 1), rad + bez, fill=(6, 6, 8, 255))
        sm = Image.new("L", (sw_, sh_), 0)
        ImageDraw.Draw(sm).rounded_rectangle((0, 0, sw_ - 1, sh_ - 1), rad, fill=255)
        ph_img.paste(screen, (15 + rim + bez, rim + bez), sm)
        if s > 0.25:
            iw = int(sw_ * 0.30)
            ih = int(iw * 0.30)
            ix = 15 + pw / 2 - iw / 2
            d.rounded_rectangle((ix, rim + bez + 24 * k, ix + iw, rim + bez + 24 * k + ih), ih / 2, fill=(0, 0, 0, 255))
        # Glanz
        gl = Image.new("RGBA", ph_img.size, (0, 0, 0, 0))
        gx = ((t - self.at) * 0.5 % 1.6 - 0.3) * ph_img.width
        ImageDraw.Draw(gl).polygon([(gx, 0), (gx + 160, 0), (gx - 300, ph), (gx - 460, ph)], fill=(255, 255, 255, int(22 * s)))
        gl.putalpha(ImageChops.multiply(gl.getchannel("A"), ph_img.getchannel("A")))
        ph_img = Image.alpha_composite(ph_img, gl)
        # 3D-Kippen
        ang = s * float(self.cfg.get("kippen", 12)) * math.sin((t - self.at) * 1.2 + 0.6)
        a = math.radians(ang)
        w2, h2 = ph_img.size
        shrink = abs(math.sin(a)) * 0.2
        dx = w2 * (1 - math.cos(a)) / 2
        dst = [(dx, 0), (w2 - dx, h2 * shrink), (w2 - dx, h2 * (1 - shrink)), (dx, h2)] if ang >= 0 else \
              [(dx, h2 * shrink), (w2 - dx, 0), (w2 - dx, h2), (dx, h2 * (1 - shrink))]
        ph_img = ph_img.transform((w2, h2), Image.PERSPECTIVE, find_coeffs(dst, [(0, 0), (w2, 0), (w2, h2), (0, h2)]), Image.BICUBIC)
        bg = frame.filter(ImageFilter.GaussianBlur(34))
        bg = Image.blend(bg, Image.new("RGB", (W, H), (8, 6, 16)), 0.6 * s).convert("RGBA")
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((W * 0.05, H * 0.15, W * 0.95, H * 0.85), fill=rgba(self.brand["accent"])[:3] + (int(110 * s),))
        bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(140)))
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(((W - w2) / 2 + 40, (H - h2) / 2 + 70, (W + w2) / 2 + 40, (H + h2) / 2 + 70), rad, fill=(0, 0, 0, int(160 * s)))
        bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(44)))
        fy = math.sin((t - self.at) * 2) * 10 * s
        bg.alpha_composite(ph_img, (int((W - w2) / 2), int((H - h2) / 2 + fy)))
        return bg


# =========================================================================== Dolly-Zoom (Vertigo)

class DollyZoom(Effect):
    """Hitchcock-Vertigo: Die Person bleibt gleich groß, der Hintergrund zoomt dramatisch – der Raum 'kippt'."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.01, 0.35)
        if pin <= 0:
            return frame
        import cv2
        rel, dur = t - self.at, max(0.5, self.until - self.at)
        m = person_mask(frame, t)
        small = np.asarray(frame.convert("RGB").resize((W // 4, H // 4)))
        ms = np.asarray(m.resize((W // 4, H // 4)).filter(ImageFilter.MaxFilter(9)))
        holes = (ms > 40).astype("uint8") * 255
        bgs = cv2.inpaint(small, holes, 7, cv2.INPAINT_TELEA)
        bg = Image.fromarray(bgs).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2))
        p = ease_in_out(clamp(rel / dur))
        strength = float(self.cfg.get("staerke", 0.45))
        z = 1 + strength * p if self.cfg.get("richtung", "rein") == "rein" else 1 + strength * (1 - p)
        cx, cy = float(self.cfg.get("cx", 0.5)), float(self.cfg.get("cy", 0.38))
        bgz = zoom_frame(bg, z, cx, cy)
        # Hintergrund-Unschärfe nimmt mit dem Zoom zu (Tiefe)
        bgz = bgz.filter(ImageFilter.GaussianBlur(3 * p))
        out = Image.blend(frame.convert("RGB"), bgz, clamp(rel * 8) * pout).convert("RGBA")
        # Person leicht gegenläufig, damit sie optisch 'steht'
        pz = 1 + 0.03 * p
        fr = zoom_frame(frame, pz, cx, cy)
        mz = zoom_frame(m.convert("RGB"), pz, cx, cy).convert("L")
        out.paste(fr.convert("RGBA"), (0, 0), mz)
        return out


# =========================================================================== Doodle-Burst

class DoodleBurst(Effect):
    """Handgezeichnete Comic-Kritzel um den Kopf: Strahlen, Sterne, Heiligenschein, Ausrufezeichen – mit 'kochenden' Linien."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.35, 0.3)
        if pin <= 0:
            return frame
        m = person_mask(frame, t)
        hx0, hy0, hx1, hy1 = head_box(m)
        cx, cy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
        hw, hh = (hx1 - hx0) / 2, (hy1 - hy0) / 2
        rng = np.random.default_rng(int(t * FPS) // 3)       # "kochende" Linien: alle 3 Frames neu gewackelt
        j = lambda s=2.2: rng.normal(0, s)
        out = frame.convert("RGBA")
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        cols = [rgba(c) for c in self.cfg.get("farben", ["#FFE14D", "#FFFFFF", "#7CF5FF"])]
        rel = t - self.at
        def stroke(pts, col, wdt=9, prog=1.0):
            n = max(2, int(len(pts) * clamp(prog)))
            if n >= 2:
                d.line([(x + j(), y + j()) for x, y in pts[:n]], fill=col[:3] + (int(255 * pout),), width=wdt, joint="curve")
        # Strahlen links/rechts
        for side in (-1, 1):
            for k in range(4):
                an = math.radians(-35 + k * 22) if side == 1 else math.radians(180 + 35 - k * 22)
                r0, r1 = hw * 1.25, hw * 1.25 + 70 + 12 * (k % 2)
                bx, by = cx + side * 0, cy - hh * 0.1
                p0 = (bx + r0 * math.cos(an), by + r0 * math.sin(an))
                p1 = (bx + r1 * math.cos(an), by + r1 * math.sin(an))
                stroke([p0, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), p1], cols[0], 10, clamp((rel - 0.05 * k) / 0.2))
        # Heiligenschein-Ellipse über dem Kopf
        pts = [(cx + hw * 0.85 * math.cos(a), hy0 - 40 + 26 * math.sin(a)) for a in np.linspace(0, 2 * math.pi * 1.08, 40)]
        stroke(pts, cols[1], 8, clamp((rel - 0.15) / 0.35))
        # Sterne
        for k, (sx, sy, r) in enumerate([(hx1 + 70, hy0 + 20, 32), (hx0 - 80, hy0 + 60, 24), (hx1 + 40, hy1 - 10, 20)]):
            a = clamp((rel - 0.25 - 0.08 * k) / 0.2)
            r *= ease_out_back(a)
            if r > 1:
                sp = [(sx + (r if i % 2 == 0 else r * 0.38) * math.cos(math.radians(i * 45 - 90)), sy + (r if i % 2 == 0 else r * 0.38) * math.sin(math.radians(i * 45 - 90))) for i in range(9)]
                stroke(sp, cols[2], 6)
        # Ausrufezeichen
        if rel > 0.35:
            el = text_img("!!", marker(110), fill=cols[0], shadow_alpha=160, pad=10).rotate(-12, resample=Image.BICUBIC, expand=True)
            paste_scaled(lay, el, hx1 + 110, hy0 - 30, 0.6 + 0.4 * ease_out_back(clamp((rel - 0.35) / 0.25)), pout)
        txt = self.cfg.get("text")
        if txt and rel > 0.45:
            el = text_img(clean_text(txt, "PermanentMarker-Regular.ttf"), marker(84), fill=(255, 255, 255, 255), shadow_alpha=180, pad=12).rotate(-5, resample=Image.BICUBIC, expand=True)
            paste_scaled(lay, el, W / 2, hy1 + 120, 0.7 + 0.3 * ease_out_back(clamp((rel - 0.45) / 0.25)), pout)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", (W, H), (0, 0, 0, 120)), (4, 6), lay.getchannel("A"))
        out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(3)))
        return Image.alpha_composite(out, lay)


# =========================================================================== Polaroid-Dump

class PolaroidDump(Effect):
    """Kamera-Blitze: Momente aus dem Video werden zu Polaroids, die sich entwickeln und als Collage landen."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.01, 0.35)
        if pin <= 0:
            return frame
        n = int(self.cfg.get("anzahl", 3))
        step = float(self.cfg.get("abstand", 0.55))
        caps = self.cfg.get("texte", ["Tag 1", "Tag 7", "Tag 30"])
        if not hasattr(self, "_shots"):
            self._shots = {}
        rel = t - self.at
        for k in range(n):
            if rel >= k * step and k not in self._shots:
                self._shots[k] = frame.copy()
        dim = 0.45 * clamp(rel * 3) * pout
        out = Image.blend(frame.convert("RGB"), Image.new("RGB", (W, H), (10, 10, 12)), dim).filter(ImageFilter.GaussianBlur(6 * dim)).convert("RGBA")
        spots = [(0.30, 0.30, -8), (0.70, 0.42, 7), (0.40, 0.66, -3), (0.68, 0.74, 10)]
        for k in sorted(self._shots):
            q = rel - k * step
            pw_, ph_ = 470, 560
            pol = Image.new("RGBA", (pw_ + 40, ph_ + 140), (0, 0, 0, 0))
            pd = ImageDraw.Draw(pol)
            pd.rectangle((20, 20, 20 + pw_, 20 + ph_ + 100), fill=(250, 248, 242, 255))
            shot = self._shots[k].resize((W // 2, H // 2)).crop((W // 4 - 215, H // 8 - 30, W // 4 + 215, H // 8 + 450)).resize((pw_ - 40, ph_ - 40))
            dev = clamp(q / 0.9)                                   # Entwickeln
            shot = Image.blend(Image.new("RGB", shot.size, (40, 34, 30)), shot, dev)
            shot = Image.blend(shot, Image.new("RGB", shot.size, (255, 245, 225)), 0.25 * (1 - dev))
            pol.paste(shot, (40, 40))
            cap = caps[k % len(caps)] if caps else ""
            if cap:
                pd.text((20 + pw_ / 2, 20 + ph_ + 40), clean_text(cap, "PermanentMarker-Regular.ttf"), font=marker(52), fill=(30, 30, 34, 255), anchor="mm")
            sh = Image.new("RGBA", pol.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).rectangle((30, 34, 30 + pw_, 34 + ph_ + 100), fill=(0, 0, 0, 120))
            pol = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)), pol)
            sx, sy, rot = spots[k % len(spots)]
            fly = ease_out_cubic(clamp(q / 0.45))
            x = W / 2 + (sx * W - W / 2) * fly
            y = H / 2 + (sy * H - H / 2) * fly
            sc = 2.0 - 1.35 * fly
            el = pol.rotate(rot * fly, resample=Image.BICUBIC, expand=True)
            paste_scaled(out, el, x, y, sc * 0.75, pout)
            fl = 1 - clamp(q / 0.12)
            if fl > 0:
                out = Image.blend(out, Image.new("RGBA", (W, H), (255, 255, 255, 255)), fl * 0.85)
        return out


# =========================================================================== VHS-Rewind

def _tri(d, x, y, s, left=True, fill=(255, 255, 255, 255)):
    if left:
        d.polygon([(x + s, y - s), (x, y), (x + s, y + s)], fill=fill)
    else:
        d.polygon([(x, y - s), (x + s, y), (x, y + s)], fill=fill)


class VHSRewind(Effect):
    """VHS-Look: Das Video spult sichtbar zurück (◀◀ REW, Bildrauschen, Spurstreifen) und läuft dann im Retro-Look weiter."""

    def apply(self, frame, t):
        look = float(self.cfg.get("rueckspulen", 1.6))
        if not hasattr(self, "_buf"):
            self._buf = deque(maxlen=int(FPS * float(self.cfg.get("zurueck", 2.5))))
        if t < self.at:
            if t > self.at - 3:
                self._buf.append(frame.resize((W // 2, H // 2)))
            return frame
        if t > self.until + 0.3:
            return frame
        rel = t - self.at
        rewinding = rel < look and len(self._buf) > 2
        if rewinding:
            idx = len(self._buf) - 1 - int(rel / look * (len(self._buf) - 1))
            src = self._buf[max(0, idx)].resize((W, H), Image.BILINEAR)
        else:
            src = frame
        fade = 1 - clamp((t - self.until) / 0.3)
        a = np.asarray(src.convert("RGB"), np.float32)
        # Farbbluten + Entsättigung + Rauschen
        a[..., 0] = np.roll(a[..., 0], 6, axis=1)
        a[..., 2] = np.roll(a[..., 2], -4, axis=1)
        gray = a.mean(axis=2, keepdims=True)
        a = a * 0.75 + gray * 0.25
        a = (a - 128) * 0.9 + 128 + np.array([8, 0, -6], np.float32)
        rng = np.random.default_rng(int(t * 1000))
        a += rng.normal(0, 10 if rewinding else 5, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
        a[::4] *= 0.86
        out = np.clip(a, 0, 255).astype("uint8")
        # Spurstreifen
        n_bands = 3 if rewinding else 1
        for k in range(n_bands):
            y0 = int((t * (900 if rewinding else 120) + k * 640) % H)
            hgt = 28 if rewinding else 14
            out[y0:y0 + hgt] = np.roll(out[y0:y0 + hgt], int(rng.integers(20, 90)), axis=1)
            out[y0:y0 + 4] = np.clip(out[y0:y0 + 4].astype(np.int16) + 120, 0, 255).astype("uint8")
        img = Image.fromarray(out).convert("RGBA")
        d = ImageDraw.Draw(img)
        mono = font_named("CourierPrime-Bold.ttf", 64)
        white = (255, 255, 255, 255)
        if rewinding:
            if int(t * 3) % 2 == 0:
                _tri(d, 70, 130, 26, True, white)
                _tri(d, 100, 130, 26, True, white)
                d.text((150, 130), "REW", font=mono, fill=white, anchor="lm")
        else:
            if rel < look + 1.5:
                _tri(d, 80, 130, 26, False, white)
                d.text((130, 130), "PLAY", font=mono, fill=white, anchor="lm")
        d.text((70, H - 150), self.cfg.get("datum", "OKT. 28 2026"), font=font_named("CourierPrime-Bold.ttf", 48), fill=white)
        sec = int(rel * 10) if not rewinding else max(0, 99 - int(rel * 40))
        d.text((W - 70, H - 150), f"0:00:{sec % 60:02d}", font=font_named("CourierPrime-Bold.ttf", 48), fill=white, anchor="ra")
        return Image.blend(frame.convert("RGBA"), img, fade) if fade < 1 else img


# =========================================================================== Bento-Grid

class BentoGrid(Effect):
    """Das Video zieht sich in eine Kachel zurück, drumherum bauen sich Bento-Kacheln auf: Kennzahl, Kurve, Tool-Logos, Headline."""

    def covers(self, t):
        return self.at <= t <= self.until

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        rel, dur = t - self.at, self.until - self.at
        tr = 0.5
        s = ease_in_out(clamp(rel / tr)) * (1 - ease_in_out(clamp((rel - (dur - tr)) / tr)))
        bg = Image.new("RGBA", (W, H), (12, 11, 16, 255))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((-200, H * 0.4, W * 0.8, H * 1.1), fill=rgba(self.brand["accent"])[:3] + (90,))
        bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(160)))
        d = ImageDraw.Draw(bg)
        M, G = 44, 20
        cw = (W - 2 * M - G) / 2
        title = self.cfg.get("titel", "Mein KI-Stack")
        ta = ease_out_cubic(clamp((rel - 0.3) / 0.4)) * s
        d.text((M, 120), clean_text(title), font=font(72, 900), fill=(255, 255, 255, int(255 * ta)))
        d.text((M, 210), clean_text(self.cfg.get("untertitel", "So spare ich 10 Stunden pro Woche")), font=font(34, 600), fill=(170, 170, 180, int(255 * ta)))
        # Video-Kachel (links, groß)
        vx0, vy0, vx1, vy1 = M, 300, M + cw, 300 + cw * 16 / 9 * 0.92
        tx0 = 0 + (vx0 - 0) * s
        ty0 = 0 + (vy0 - 0) * s
        tx1 = W + (vx1 - W) * s
        ty1 = H + (vy1 - H) * s
        vw, vh = int(tx1 - tx0), int(ty1 - ty0)
        vid = frame.convert("RGB")
        k = max(vw / W, vh / H)
        vid = vid.resize((int(W * k) + 1, int(H * k) + 1), Image.LANCZOS)
        vid = vid.crop(((vid.width - vw) // 2, int((vid.height - vh) * 0.25), (vid.width - vw) // 2 + vw, int((vid.height - vh) * 0.25) + vh))
        tiles = [
            ("zahl", M + cw + G, 300, W - M, 300 + 380),
            ("kurve", M + cw + G, 300 + 380 + G, W - M, vy1),
            ("logos", M, vy1 + G, W - M, vy1 + G + 230),
            ("text", M, vy1 + 2 * G + 230, W - M, H - 140),
        ]
        for k_, (typ, x0, y0, x1, y1) in enumerate(tiles):
            a = ease_out_back(clamp((rel - 0.35 - 0.12 * k_) / 0.45)) * s
            if a <= 0.01:
                continue
            tile = Image.new("RGBA", (int(x1 - x0), int(y1 - y0)), (0, 0, 0, 0))
            td = ImageDraw.Draw(tile)
            td.rounded_rectangle((0, 0, tile.width - 1, tile.height - 1), 36, fill=(28, 27, 34, 245), outline=(255, 255, 255, 28), width=2)
            tw_, th_ = tile.size
            if typ == "zahl":
                v = float(self.cfg.get("zahl", 10)) * ease_out_cubic(clamp((rel - 0.6) / 1.0))
                td.text((36, 40), clean_text(self.cfg.get("zahl_label", "Stunden gespart / Woche")), font=font(28, 700), fill=(170, 170, 180, 255))
                td.text((36, th_ - 60), f"{int(v)}{self.cfg.get('zahl_suffix', '+')}", font=font(170, 900), fill=rgba(self.brand["accent2"]), anchor="ls")
            elif typ == "kurve":
                td.text((36, 36), "Reichweite", font=font(28, 700), fill=(170, 170, 180, 255))
                pts = [0.1, 0.18, 0.15, 0.3, 0.38, 0.52, 0.6, 0.82, 0.95]
                pr = ease_in_out(clamp((rel - 0.7) / 1.2))
                n = max(2, int(len(pts) * pr))
                xy = [(36 + (tw_ - 72) * i / (len(pts) - 1), th_ - 40 - (th_ - 130) * p) for i, p in enumerate(pts[:n])]
                td.line(xy, fill=rgba(self.brand["green"]), width=8, joint="curve")
                hx, hy = xy[-1]
                td.ellipse((hx - 12, hy - 12, hx + 12, hy + 12), fill=(255, 255, 255, 255))
            elif typ == "logos":
                td.text((36, 30), "Mein Stack", font=font(28, 700), fill=(170, 170, 180, 255))
                names = self.cfg.get("logos", ["claude", "higgsfield", "elevenlabs", "notion", "canva", "gmail"])
                sz = 120
                for i, nm in enumerate(names[:6]):
                    lg = app_logo(nm, sz)
                    la = ease_out_back(clamp((rel - 0.8 - 0.08 * i) / 0.35))
                    if lg is not None and la > 0:
                        lg = lg.resize((max(1, int(sz * la)), max(1, int(sz * la))))
                        tile.alpha_composite(lg, (int(36 + i * (sz + 30) + (sz - lg.width) / 2), int(80 + (sz - lg.height) / 2)))
            else:
                td.text((40, th_ / 2 - 40), clean_text(self.cfg.get("text", "Ein Befehl.")), font=font(64, 900), fill=(255, 255, 255, 255), anchor="lm")
                td.text((40, th_ / 2 + 40), clean_text(self.cfg.get("text2", "Fertiges Reel.")), font=bodoni(64, 500, italic=True), fill=rgba(self.brand["accent2"]), anchor="lm")
            paste_scaled(bg, tile, (x0 + x1) / 2, (y0 + y1) / 2, 0.85 + 0.15 * a, clamp(a))
        vm = Image.new("L", (vw, vh), 0)
        ImageDraw.Draw(vm).rounded_rectangle((0, 0, vw - 1, vh - 1), int(36 * s), fill=255)
        bg.paste(vid, (int(tx0), int(ty0)), vm)
        return bg


V3 = {
    "magazin-cover": VogueCover,
    "ki-scan": AIScanHollywood,
    "freeze-sticker": FreezeStickerPro,
    "handy-portal": InstaPhone,
    "dolly-zoom": DollyZoom,
    "doodle-burst": DoodleBurst,
    "polaroid-dump": PolaroidDump,
    "vhs-rewind": VHSRewind,
    "bento-grid": BentoGrid,
}


# =========================================================================== Glas-Chart v2 (nah an der Referenz)

class GlassChartPro(Effect):
    """Klare Glasplatte (kaum getönt), Mono-Label mit Sperrung, große Zahl mit kleinem %, feine Rasterlinien,
    grüne Linie mit Fläche, die an einer harten Kante endet, weißer Punkt mit grünem Ring."""

    def occupied(self, t):
        if self.at <= t <= self.until + 0.3:
            cy = float(self.cfg.get("y", 0.71)) * H
            h = int(self.cfg.get("h", 580))
            return (cy - h / 2, cy + h / 2)

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.5, 0.35)
        if pin <= 0:
            return frame
        a = ease_out_cubic(pin) * pout
        cw, ch = int(self.cfg.get("w", 850)), int(self.cfg.get("h", 580))
        cy = float(self.cfg.get("y", 0.71)) * H
        x0 = (W - cw) / 2
        y0 = cy - ch / 2 + (1 - ease_out_cubic(pin)) * 70
        grow = ease_in_out(clamp((t - self.at - 0.2) / float(self.cfg.get("grow", 1.8))))
        frame = frame.convert("RGBA")
        # Glas: leichter Blur + kaum Tönung, damit die Hände durchscheinen
        box = (int(x0), int(y0), int(x0 + cw), int(y0 + ch))
        reg = frame.crop(box).filter(ImageFilter.GaussianBlur(6))
        reg = Image.alpha_composite(reg, Image.new("RGBA", reg.size, (12, 14, 16, 62)))
        mk = Image.new("L", reg.size, 0)
        ImageDraw.Draw(mk).rounded_rectangle((0, 0, cw - 1, ch - 1), 34, fill=int(255 * a))
        frame.paste(reg, box[:2], mk)
        lay = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        # Rand + obere Lichtkante
        d.rounded_rectangle((0, 0, cw - 1, ch - 1), 34, outline=(255, 255, 255, 95), width=2)
        d.rounded_rectangle((2, 2, cw - 3, ch - 3), 32, outline=(255, 255, 255, 25), width=1)
        hl = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        ImageDraw.Draw(hl).rounded_rectangle((0, 0, cw - 1, ch - 1), 34, outline=(255, 255, 255, 170), width=3)
        grad = Image.linear_gradient("L").resize((cw, ch)).point(lambda v: max(0, 255 - v * 4))
        hl.putalpha(ImageChops.multiply(hl.getchannel("A"), grad))
        lay = Image.alpha_composite(lay, hl)
        d = ImageDraw.Draw(lay)
        # Label + Zahl
        label = " ".join(self.cfg.get("label", "RETENTION").upper())
        d.text((40, 96), label, font=font_named("CourierPrime-Regular.ttf", 30), fill=(225, 225, 228, 235), anchor="lm")
        val = float(self.cfg.get("value", 67)) * grow
        dec = int(self.cfg.get("decimals", 0))
        num = f"{val:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        num = self.cfg.get("prefix", "") + num
        suf = self.cfg.get("suffix", "%")
        fv, fs = font(84, 800), font(42, 800)
        sw = fs.getlength(suf)
        d.text((cw - 38 - sw - 4, 118), num, font=fv, fill=(255, 255, 255, 255), anchor="rs")
        d.text((cw - 38, 118), suf, font=fs, fill=(255, 255, 255, 240), anchor="rs")
        # Raster
        gx0, gx1, gy0, gy1 = 36, cw - 36, 180, ch - 50
        for k in range(1, 4):
            yy = gy0 + (gy1 - gy0) * k / 4
            d.line((gx0, yy, gx1, yy), fill=(255, 255, 255, 22), width=2)
        # Kurve
        pts = [float(p) for p in self.cfg.get("points", [0.06, 0.09, 0.13, 0.17, 0.2, 0.28, 0.36, 0.44, 0.58, 0.74])]
        n = len(pts)
        xy = [(gx0 + (gx1 - gx0) * i / (n - 1), gy1 - (gy1 - gy0) * p) for i, p in enumerate(pts)]
        pos = grow * (n - 1)
        k = int(pos)
        vis = xy[: k + 1]
        if k < n - 1:
            fr = pos - k
            vis.append((xy[k][0] + (xy[k + 1][0] - xy[k][0]) * fr, xy[k][1] + (xy[k + 1][1] - xy[k][1]) * fr))
        col = rgba(self.cfg.get("color", "#22C55E"))
        if len(vis) >= 2:
            fill = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            ImageDraw.Draw(fill).polygon(vis + [(vis[-1][0], gy1 + 40), (vis[0][0], gy1 + 40)], fill=col[:3] + (255,))
            g2 = Image.new("L", (cw, ch), 0)
            gd = ImageDraw.Draw(g2)
            top = min(p[1] for p in vis)
            for yy in range(int(top), ch):
                gd.line((0, yy, cw, yy), fill=int(150 * max(0, 1 - (yy - top) / (gy1 + 40 - top))))
            fill.putalpha(ImageChops.multiply(fill.getchannel("A"), g2))
            lay = Image.alpha_composite(lay, fill)
            d = ImageDraw.Draw(lay)
            d.line((vis[-1][0], vis[-1][1], vis[-1][0], gy1 + 40), fill=col[:3] + (90,), width=2)
            gl = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            ImageDraw.Draw(gl).line(vis, fill=col[:3] + (200,), width=14, joint="curve")
            lay = Image.alpha_composite(lay, gl.filter(ImageFilter.GaussianBlur(8)))
            d = ImageDraw.Draw(lay)
            d.line(vis, fill=col, width=7, joint="curve")
            hx, hy = vis[-1]
            d.ellipse((hx - 14, hy - 14, hx + 14, hy + 14), fill=col)
            d.ellipse((hx - 8, hy - 8, hx + 8, hy + 8), fill=(255, 255, 255, 255))
        frame.alpha_composite(alpha_mul(lay, a), box[:2])
        return frame


V3["glas-chart"] = GlassChartPro


# =========================================================================== Carousel-Spin (Reels steigen aus dem Handy auf)

class CarouselSpin(Effect):
    """POV: Handy in der Hand – die Reels fliegen aus dem Display auf einen 3D-Ring über dem Handy und werden Karte für Karte gewischt.
    Das Handy wird automatisch gefunden und verfolgt (helles Display im unteren Bildteil)."""

    def _find_phone(self, frame):
        import cv2
        g = np.asarray(frame.convert("L"), np.uint8)
        y0 = int(H * float(self.cfg.get("suche_ab", 0.40)))
        sub = g[y0:]
        _, th = cv2.threshold(cv2.GaussianBlur(sub, (21, 21), 0), int(self.cfg.get("hell", 150)), 255, cv2.THRESH_BINARY)
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
        n, lab, st, cen = cv2.connectedComponentsWithStats(th)
        best = None
        for i in range(1, n):
            x, y, w, h, a = st[i]
            if a < 4000 or h < w * 0.9:          # Handy steht hochkant
                continue
            score = a * (1.5 if h > w * 1.4 else 1)
            if best is None or score > best[0]:
                best = (score, x, y + y0, w, h)
        if best is None:
            return (W * float(self.cfg.get("handy_x", 0.4)), H * float(self.cfg.get("handy_y", 0.62)), 260, 480)
        _, x, y, w, h = best
        return (x + w / 2, y + h / 2, w, h)

    def _track(self, frame):
        import cv2
        g = np.asarray(frame.convert("L"), np.uint8)
        if not hasattr(self, "_tpl"):
            cx, cy, w, h = self._find_phone(frame)
            self._box = [cx, cy, w, h]
            x0, y0 = int(cx - w / 2), int(cy - h / 2)
            self._tpl = g[max(0, y0):y0 + int(h), max(0, x0):x0 + int(w)].copy()
            return self._box
        cx, cy, w, h = self._box
        r = 90
        X0, Y0 = int(max(0, cx - w / 2 - r)), int(max(0, cy - h / 2 - r))
        X1, Y1 = int(min(W, cx + w / 2 + r)), int(min(H, cy + h / 2 + r))
        win = g[Y0:Y1, X0:X1]
        if win.shape[0] > self._tpl.shape[0] and win.shape[1] > self._tpl.shape[1]:
            res = cv2.matchTemplate(win, self._tpl, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if mx > 0.35:
                ncx = X0 + loc[0] + self._tpl.shape[1] / 2
                ncy = Y0 + loc[1] + self._tpl.shape[0] / 2
                self._box[0] = 0.6 * self._box[0] + 0.4 * ncx
                self._box[1] = 0.6 * self._box[1] + 0.4 * ncy
        return self._box

    def _cards(self):
        from effects import MediaReader, phone_card
        paths = self.cfg.get("images") or []
        labels = self.cfg.get("labels", [])
        n = int(self.cfg.get("count", max(7, len(paths))))
        self._src = []
        for k in range(n):
            p = paths[k % len(paths)] if paths else None
            if p and str(p).lower().endswith((".mp4", ".mov", ".m4v")):
                self._src.append(("v", MediaReader(p, (300, 534))))
            elif p:
                self._src.append(("i", Image.open(p).convert("RGB")))
            else:
                self._src.append(("i", None))
        self._labels = labels
        self._pc = phone_card

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.01, 0.35)
        if pin <= 0:
            return frame
        if not hasattr(self, "_src"):
            self._cards()
        pcx, pcy, pw, ph = self._track(frame)
        rel = t - self.at
        dim = 0.42 * clamp(rel * 2.5) * pout
        bg = frame.filter(ImageFilter.GaussianBlur(5 * dim / 0.42)).convert("RGBA")
        bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (0, 0, 0, int(255 * dim))))
        # Lichtkegel aus dem Display
        cone = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        top = pcy - ph / 2
        ring_y = max(H * 0.24, top - float(self.cfg.get("hoehe", 430)))
        ImageDraw.Draw(cone).polygon([(pcx - pw * 0.35, top), (pcx + pw * 0.35, top), (pcx + W * 0.42, ring_y), (pcx - W * 0.42, ring_y)],
                                     fill=(170, 150, 255, int(70 * clamp(rel * 2) * pout)))
        bg = Image.alpha_composite(bg, cone.filter(ImageFilter.GaussianBlur(40)))
        n = len(self._src)
        R = float(self.cfg.get("radius", 400))
        step = 2 * math.pi / n
        if self.cfg.get("finger_sync", True) and self.cfg.get("_input"):
            if not hasattr(self, "_cum"):
                dx = finger_motion(self.cfg["_input"], float(self.cfg.get("_start", 0)))
                # Nur der schnelle Wisch (Finger auf dem Display) dreht – das Zurückführen des Fingers nicht
                d0 = float(np.sign(dx[np.argmax(np.abs(dx))])) or -1.0
                dx = np.where((np.sign(dx) == d0) & (np.abs(dx) > 6.0), dx, 0.0)
                cum = np.cumsum(dx)
                # Wisch-Amplituden → Verstärkung, damit ein Wisch ≈ eine Karte weiterdreht
                amps, cur = [], 0.0
                for v in dx:
                    if abs(v) > 0:
                        cur += v
                    elif cur:
                        amps.append(abs(cur)); cur = 0.0
                amp = float(np.median(amps)) if amps else 300.0
                self._gain = float(self.cfg.get("finger_gain", 0)) or step / max(60.0, amp)
                sm = np.copy(cum)
                for i in range(1, len(sm)):                       # leichtes Glätten
                    sm[i] = 0.55 * sm[i - 1] + 0.45 * cum[i]
                self._cum = sm
            i = min(len(self._cum) - 1, max(0, int(round(t * FPS))))
            base = self._cum[min(len(self._cum) - 1, int(round(self.at * FPS)))]
            spin = (self._cum[i] - base) * self._gain * float(self.cfg.get("richtung", 1))
        else:
            sw = float(self.cfg.get("swipe", 0.7))
            r2 = max(0.0, rel - 0.7)
            steps = int(r2 / sw) + ease_out_cubic(clamp((r2 % sw) / (sw * 0.55)))
            spin = -steps * step
        emerge = ease_out_cubic(clamp(rel / 0.75))
        ringx = pcx * 0.35 + W / 2 * 0.65
        placed = []
        for k, (typ, src) in enumerate(self._src):
            th = spin + 2 * math.pi * k / n
            x, z = R * math.sin(th), R * math.cos(th)
            persp = 1000 / (1000 - z * 0.9)
            placed.append((z, k, typ, src, x, th, persp))
        for z, k, typ, src, x, th, persp in sorted(placed, key=lambda q: q[0]):
            img = src.get(rel) if typ == "v" else src
            card = self._pc(img, w=300, h=534, label=self._labels[k] if k < len(self._labels) else None, brand=self.brand)
            face = 0.3 + 0.7 * abs(math.cos(th))
            sc = persp * 0.78
            tx, ty = ringx + x, ring_y - z * 0.12
            # Auftauchen aus dem Display
            e = clamp(emerge * 1.3 - (1 - (z / R + 1) / 2) * 0.3)
            cx_ = pcx + (tx - pcx) * e
            cy_ = (top + ph * 0.25) + (ty - (top + ph * 0.25)) * e
            sc *= 0.25 + 0.75 * e
            el = card.resize((max(2, int(card.width * face * sc)), max(2, int(card.height * sc))), Image.LANCZOS)
            shade = clamp(0.45 + 0.55 * (z / R + 1) / 2)
            if shade < 0.99:
                a = np.asarray(el, np.float32)
                a[..., :3] *= shade
                el = Image.fromarray(a.astype("uint8"))
            paste_scaled(bg, el, cx_, cy_, 1.0, clamp(e * 2) * pout)
        # Hand + Handy wieder nach vorne (Person-Maske erkennt die Hand)
        if self.cfg.get("hand_vorne", True):
            m = person_mask(frame, t)
            sharp = frame.convert("RGBA")
            bg.paste(sharp, (0, 0), m.point(lambda v: int(v * 0.9)))
        return bg


V3["carousel-spin"] = CarouselSpin


# =========================================================================== Fingerbewegung messen (für Carousel-Spin)

def finger_motion(path, start=0.0, fps=FPS, region=(0.40, 0.88)):
    """Horizontale Bewegung der Hand pro Frame (Pixel bei 1080 Breite), Kamerawackeln herausgerechnet."""
    import subprocess as sp
    import cv2
    from reelkit import ffmpeg_bin
    w, h = 270, 480
    raw = sp.run([ffmpeg_bin(), "-v", "error", "-ss", str(start), "-i", path, "-vf",
                  f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                 capture_output=True, check=True).stdout
    n = len(raw) // (w * h)
    fr = np.frombuffer(raw[: n * w * h], np.uint8).reshape(n, h, w)
    dx = np.zeros(n, np.float32)
    y0, y1 = int(h * region[0]), int(h * region[1])
    for i in range(1, n):
        flow = cv2.calcOpticalFlowFarneback(fr[i - 1], fr[i], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        fx = flow[..., 0]
        cam = np.median(fx[: int(h * 0.3)])                  # Kamera-/Bildschirmbewegung oben
        roi = fx[y0:y1] - cam
        mag = np.abs(roi)
        thr = np.percentile(mag, 92)
        sel = roi[mag >= max(thr, 0.6)]
        dx[i] = float(sel.mean()) * (W / w) if sel.size else 0.0
    return dx


# =========================================================================== Körper-Orbit (Reels kreisen um die Person)

class BodyOrbit(Effect):
    """Reel-Karten kreisen auf einem 3D-Ring um den Körper: vorne vor der Person, hinten hinter ihr (Freistellung)."""

    def _prep(self):
        from effects import MediaReader
        paths = self.cfg.get("images") or []
        n = int(self.cfg.get("count", max(7, len(paths))))
        self._src = []
        for k in range(n):
            p = paths[k % len(paths)] if paths else None
            if p and str(p).lower().endswith((".mp4", ".mov", ".m4v")):
                self._src.append(("v", MediaReader(p, (300, 534))))
            else:
                self._src.append(("i", Image.open(p).convert("RGB") if p else None))
        self._labels = self.cfg.get("labels", [])

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.01, 0.35)
        if pin <= 0:
            return frame
        from effects import phone_card
        if not hasattr(self, "_src"):
            self._prep()
        rel = t - self.at
        m = person_mask(frame, t)
        n = len(self._src)
        grow = spring(clamp(rel / 0.9), 5.5, 1.1)
        R = float(self.cfg.get("radius", 470)) * (0.35 + 0.65 * grow)
        cy = float(self.cfg.get("y", 0.56)) * H
        spin = 2 * math.pi * float(self.cfg.get("speed", 0.14)) * rel + float(self.cfg.get("start_winkel", 0.0))
        back = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        items = []
        for k, (typ, src) in enumerate(self._src):
            th = spin + 2 * math.pi * k / n
            x, z = R * math.sin(th), R * math.cos(th)
            items.append((z, k, typ, src, x, th))
        for z, k, typ, src, x, th in sorted(items, key=lambda q: q[0]):
            img = src.get(rel) if typ == "v" else src
            card = phone_card(img, w=300, h=534, label=self._labels[k] if k < len(self._labels) else None, brand=self.brand)
            persp = 1100 / (1100 - z * 0.8)
            face = 0.55 + 0.45 * abs(math.cos(th))
            el = card.resize((max(2, int(card.width * face * persp * 0.82)), max(2, int(card.height * persp * 0.82))), Image.LANCZOS)
            el = el.rotate(-math.sin(th) * 9, resample=Image.BICUBIC, expand=True)
            if z < 0:
                a = np.asarray(el, np.float32)
                a[..., :3] *= 0.62 + 0.38 * (1 + z / max(1, R))
                el = Image.fromarray(a.astype("uint8"))
            tgt = front if z >= 0 else back
            paste_scaled(tgt, el, W / 2 + x, cy + z * 0.16, 1.0, clamp(rel * 4) * pout)
        out = Image.alpha_composite(frame.convert("RGBA"), back)
        out.paste(frame.convert("RGBA"), (0, 0), m)
        return Image.alpha_composite(out, front)


V3["koerper-orbit"] = BodyOrbit
