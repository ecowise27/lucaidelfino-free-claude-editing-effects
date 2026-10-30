"""Pro-Effekte: alles, was die Person freistellt oder das ganze Bild verwandelt.

Wird am Ende von effects.py importiert und in REGISTRY eingetragen.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from effects import Effect, clean_text, load_words, text_img
from reelkit import (H, W, clamp, ease_in_out, ease_out_back, ease_out_cubic, font, font_named, glass, paste_scaled,
                     rgba, spring, text_size, window, zoom_frame)

# --------------------------------------------------------------------------- gemeinsame Freistellung

_SEG = None
_CACHE = {"t": None, "m": None}


def person_mask(frame, t, quality="fast"):
    """Maske der Person (L, 255 = Person); pro Frame nur einmal berechnet, auch wenn mehrere Effekte sie brauchen."""
    global _SEG
    if _CACHE["t"] == t and _CACHE["m"] is not None:
        return _CACHE["m"]
    if _SEG is None:
        from segment import Segmenter
        _SEG = Segmenter(quality)
    m = _SEG.mask(frame, t)
    _CACHE.update(t=t, m=m)
    return m


def cutout(frame, mask):
    c = frame.convert("RGBA")
    c.putalpha(mask)
    return c


def bbox(mask, thr=128):
    a = np.asarray(mask.resize((W // 4, H // 4)))
    ys, xs = np.nonzero(a > thr)
    if not len(xs):
        return (W * 0.3, H * 0.25, W * 0.7, H * 0.9)
    return (xs.min() * 4, ys.min() * 4, xs.max() * 4, ys.max() * 4)


def head_box(mask):
    x0, y0, x1, y1 = bbox(mask)
    a = np.asarray(mask.resize((W // 4, H // 4)))
    top = int(y0 // 4)
    rows = a[top:top + int(0.22 * H / 4)]
    cols = np.nonzero((rows > 128).any(axis=0))[0]
    hx0, hx1 = (cols.min() * 4, cols.max() * 4) if len(cols) else (x0, x1)
    hw = hx1 - hx0
    return (hx0, y0, hx1, y0 + hw * 1.25)


def duotone(img, dark, light):
    g = ImageOps.grayscale(img)
    return ImageOps.colorize(g, dark, light)


def find_coeffs(dst, src):
    """Koeffizienten für Image.PERSPECTIVE (dst = Zielecken, src = Quellecken)."""
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.array(m, dtype=np.float64)
    b = np.array(src, dtype=np.float64).reshape(8)
    return np.linalg.solve(A, b).tolist()


def additive(base: Image.Image, light: np.ndarray):
    """light = float-Array (H, W, 3) 0..255, wird aufaddiert (Leuchten)."""
    a = np.asarray(base.convert("RGB"), dtype=np.float32) + light
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


# =========================================================================== Neon-Kontur

class NeonContour(Effect):
    """Leuchtende Neon-Linie zeichnet sich um die Person, pulsiert, Hintergrund wird dunkler."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.9, 0.35)
        if pin <= 0:
            return frame
        m = person_mask(frame, t)
        sw, sh = 270, 480
        ms = m.resize((sw, sh))
        a = np.asarray(ms, np.float32) / 255
        d1 = np.asarray(ms.filter(ImageFilter.MaxFilter(5)), np.float32) / 255
        d2 = np.asarray(ms.filter(ImageFilter.MaxFilter(11)), np.float32) / 255
        d3 = np.asarray(ms.filter(ImageFilter.MaxFilter(15)), np.float32) / 255
        e1 = np.clip(d1 - a, 0, 1)
        e2 = np.clip(d3 - d2, 0, 1)
        ys, xs = np.nonzero(a > 0.5)
        cx, cy = (xs.mean(), ys.mean()) if len(xs) else (sw / 2, sh / 2)
        Y, X = np.mgrid[0:sh, 0:sw]
        ang = ((np.arctan2(Y - cy, X - cx) + math.pi / 2) % (2 * math.pi)) / (2 * math.pi)
        rv = ease_in_out(pin)
        v1 = np.clip((rv - ang) * 25, 0, 1)
        v2 = np.clip((rv - 0.12 - ang) * 25, 0, 1)
        pulse = 0.82 + 0.18 * math.sin(t * 7)
        c1 = np.array(rgba(self.cfg.get("color", self.brand["accent2"]))[:3], np.float32)
        c2 = np.array(rgba(self.cfg.get("color2", "#3DF5C8"))[:3], np.float32)
        def up(x, blur):
            im = Image.fromarray((np.clip(x, 0, 1) * 255).astype("uint8")).resize((W, H), Image.BILINEAR)
            return np.asarray(im.filter(ImageFilter.GaussianBlur(blur)) if blur else im, np.float32)[..., None] / 255
        core1, glow1 = up(e1 * v1, 1.2), up(e1 * v1, 16)
        core2, glow2 = up(e2 * v2, 1.2), up(e2 * v2, 22)
        k = pout * pulse
        bgdim = 1 - float(self.cfg.get("dim", 0.45)) * clamp(pin * 2) * pout * (1 - np.asarray(m, np.float32)[..., None] / 255)
        base = np.asarray(frame.convert("RGB"), np.float32) * bgdim
        light = (core1 * (255 * 0.9) + glow1 * c1 * 2.6 + core2 * c2 * 1.1 + glow2 * c2 * 2.0) * k
        light += core1 * c1 * 0.6 * k
        return Image.fromarray(np.clip(base + light, 0, 255).astype("uint8"))


# =========================================================================== Klon-Echo

class CloneEcho(Effect):
    """Die Person wird links und rechts in Markenfarben geklont – fächert sich auf und wieder zusammen."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.7, 0.45)
        if pin <= 0:
            return frame
        m = person_mask(frame, t)
        cut = cutout(frame, m)
        n = int(self.cfg.get("anzahl", 3))
        spread = float(self.cfg.get("abstand", 230)) * spring(clamp(pin * 0.9), 5.5, 1.1) * (pout ** 0.6)
        cols = [rgba(c)[:3] for c in self.cfg.get("farben", [self.brand["accent"], "#3DF5C8", self.brand["accent2"]])]
        out = frame.convert("RGBA")
        out = Image.alpha_composite(out, Image.new("RGBA", (W, H), (0, 0, 0, int(90 * clamp(pin * 2) * pout))))
        g = ImageOps.grayscale(frame)
        for k in range(n, 0, -1):
            col = cols[(k - 1) % len(cols)]
            tint = ImageOps.colorize(g, (10, 6, 20), col).convert("RGBA")
            a = np.asarray(m, np.float32) * (0.85 - 0.18 * (k - 1)) * clamp(pin * 2)
            tint.putalpha(Image.fromarray(a.astype("uint8")))
            s = 1 - 0.035 * k
            el = tint.resize((int(W * s), int(H * s)), Image.LANCZOS)
            for side in (-1, 1):
                out.alpha_composite(el, (int((W - el.width) / 2 + side * spread * k), int((H - el.height) * 0.9)))
        out.alpha_composite(cut)
        return out


# =========================================================================== Freeze-Sticker

class FreezeSticker(Effect):
    """Bild friert ein, die Person wird zum Sticker mit weißem Rand, Hintergrund s/w – dazu eine Beschriftung mit Pfeil."""

    def covers(self, t):
        return self.at <= t <= self.until

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            if t > self.until:
                self.__dict__.pop("_frozen", None)
            return frame
        if not hasattr(self, "_frozen"):
            mk = person_mask(frame, t)
            half = mk.resize((W // 2, H // 2))
            stroke = half.filter(ImageFilter.MaxFilter(int(self.cfg.get("rand", 15)) | 1)).resize((W, H), Image.BILINEAR)
            stroke = stroke.point(lambda v: 255 if v > 90 else 0).filter(ImageFilter.GaussianBlur(1.2))
            bg = ImageOps.grayscale(frame).convert("RGB").filter(ImageFilter.GaussianBlur(6))
            bg = Image.blend(bg, Image.new("RGB", (W, H), (8, 8, 10)), 0.45)
            sticker = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            white = Image.new("RGBA", (W, H), (255, 255, 255, 255))
            sticker.paste(white, (0, 0), stroke)
            sticker.alpha_composite(cutout(frame, mk))
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shadow.paste(Image.new("RGBA", (W, H), (0, 0, 0, 160)), (14, 24), stroke)
            self._frozen = (frame.copy(), bg, sticker, shadow.filter(ImageFilter.GaussianBlur(18)), head_box(mk))
        orig, bg, sticker, shadow, hb = self._frozen
        rel = t - self.at
        p = ease_out_cubic(clamp(rel / 0.35))
        out = Image.blend(orig.convert("RGB"), bg, p).convert("RGBA")
        s = 1 + 0.06 * spring(clamp(rel / 0.6), 6, 1.4)
        rot = -2.5 * ease_out_cubic(clamp(rel / 0.5))
        lay = Image.alpha_composite(shadow, sticker)
        if abs(rot) > 0.05 or abs(s - 1) > 0.002:
            lay = lay.rotate(rot, resample=Image.BICUBIC, center=(W / 2, H * 0.7))
            lay = lay.resize((int(W * s), int(H * s)), Image.LANCZOS)
            lay = lay.crop(((lay.width - W) // 2, int((lay.height - H) * 0.75), (lay.width - W) // 2 + W, int((lay.height - H) * 0.75) + H))
        out.alpha_composite(lay)
        label = self.cfg.get("label")
        if label and rel > 0.25:
            la = ease_out_cubic(clamp((rel - 0.25) / 0.35))
            f = font_named("InstrumentSerif-400-italic.ttf", int(self.cfg.get("size", 96)))
            el = text_img(clean_text(label, "InstrumentSerif-400-italic.ttf"), f, fill=rgba(self.cfg.get("color", "#FFFFFF")), shadow_alpha=200, pad=20)
            side = self.cfg.get("seite", "links")
            lx = W * (0.30 if side == "links" else 0.70)
            ly = max(170, hb[1] - 30)
            paste_scaled(out, el, lx, ly + (1 - la) * 25, 1.0, la)
            d = ImageDraw.Draw(out)
            ax0, ay0 = lx + (90 if side == "links" else -90), ly + el.height / 2
            ax1, ay1 = (hb[0] - 10, hb[1] + (hb[3] - hb[1]) * 0.35) if side == "links" else (hb[2] + 10, hb[1] + (hb[3] - hb[1]) * 0.35)
            pts = []
            for i in range(21):
                q = i / 20 * la
                bx = ax0 + (ax1 - ax0) * q
                by = ay0 + (ay1 - ay0) * q - math.sin(q * math.pi) * 60
                pts.append((bx, by))
            if len(pts) > 1:
                d.line(pts, fill=(255, 255, 255, 255), width=7, joint="curve")
                if la > 0.95:
                    ex, ey = pts[-1]
                    px, py = pts[-3]
                    an = math.atan2(ey - py, ex - px)
                    for da in (2.6, -2.6):
                        d.line((ex, ey, ex + 34 * math.cos(an + da), ey + 34 * math.sin(an + da)), fill=(255, 255, 255, 255), width=7)
        flash = 1 - clamp(rel / 0.12)
        if flash > 0:
            out = Image.blend(out, Image.new("RGBA", (W, H), (255, 255, 255, 255)), flash * 0.75)
        return out


# =========================================================================== Magazin-Cover

class MagazineCover(Effect):
    """Das Video wird zum Magazin-Cover: Titel HINTER dem Kopf, roter Rahmen, Coverzeilen, Barcode."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.9, 0.35)
        if pin <= 0:
            return frame
        rel = t - self.at
        m = person_mask(frame, t)
        z = 1 + 0.05 * ease_out_cubic(clamp(rel / 2.5))
        fr = zoom_frame(frame, z, cy=0.4)
        mz = zoom_frame(m.convert("RGB"), z, cy=0.4).convert("L")
        out = fr.convert("RGBA")
        red = rgba(self.cfg.get("color", "#E3242B"))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        title = self.cfg.get("titel", "LUCA").upper()
        size = 380
        ft = font_named("InstrumentSerif-400.ttf", size)
        while text_size(title, ft)[0] > W * 0.92 and size > 120:
            size -= 10
            ft = font_named("InstrumentSerif-400.ttf", size)
        tp = ease_out_cubic(clamp((rel - 0.15) / 0.6))
        tl = text_img(title, ft, fill=rgba(self.cfg.get("titelfarbe", "#FFFFFF")), shadow_alpha=110, pad=20)
        if not hasattr(self, "_ty"):   # Titel so setzen, dass der Kopf ihn unten überdeckt
            hb = head_box(mz)
            self._ty = max(60 + tl.height / 2, hb[1] + 20)
        paste_scaled(lay, tl, W / 2, self._ty - (1 - tp) * 120, 1.0, tp * pout)
        out = Image.alpha_composite(out, lay)
        out.paste(fr.convert("RGBA"), (0, 0), mz.point(lambda v: int(v * clamp(rel * 3))))   # Person vor den Titel
        d = ImageDraw.Draw(out)
        bp = ease_in_out(clamp(rel / 0.6)) * pout
        bw = 34
        if bp > 0:
            L = (2 * W + 2 * H) * bp
            segs = [((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))]
            for (x0, y0), (x1, y1) in segs:
                ln = math.hypot(x1 - x0, y1 - y0)
                q = clamp(L / ln)
                if q <= 0:
                    break
                d.line((x0, y0, x0 + (x1 - x0) * q, y0 + (y1 - y0) * q), fill=red, width=bw * 2)
                L -= ln
        kick = self.cfg.get("ausgabe", "AUSGABE 01 · 2026")
        d.text((W - 70, 72), kick, font=font(24, 800), fill=(255, 255, 255, int(230 * tp * pout)), anchor="ra")
        lines = self.cfg.get("zeilen", ["Der KI-Creator", "So nutzt du Claude", "Die 5 besten Tools"])
        y = H * float(self.cfg.get("zeilen_y", 0.58))
        for k, ln in enumerate(lines):
            lp = ease_out_cubic(clamp((rel - 0.5 - 0.22 * k) / 0.4)) * pout
            if lp <= 0:
                continue
            f = font(52 if k == 0 else 40, 900 if k == 0 else 800)
            el = text_img(clean_text(ln.upper() if k == 0 else ln), f, fill=red if k == 0 else (255, 255, 255, 255), shadow_alpha=200, pad=10)
            out.alpha_composite(Image.fromarray(np.dstack([np.asarray(el)[..., :3], (np.asarray(el)[..., 3] * lp).astype("uint8")])),
                                (int(70 - (1 - lp) * 60), int(y)))
            y += el.height + 6
        if rel > 1.0:  # Barcode
            bp2 = ease_out_cubic(clamp((rel - 1.0) / 0.4)) * pout
            rng = np.random.default_rng(7)
            bx, by = W - 230, H - 230
            d.rectangle((bx - 14, by - 14, bx + 160, by + 120), fill=(255, 255, 255, int(255 * bp2)))
            x = bx
            while x < bx + 146:
                wbar = int(rng.integers(2, 7))
                if rng.random() > 0.4:
                    d.rectangle((x, by, x + wbar, by + 88), fill=(10, 10, 10, int(255 * bp2)))
                x += wbar + 2
            d.text((bx + 73, by + 104), "4 001234 567890", font=font(14, 700), fill=(10, 10, 10, int(255 * bp2)), anchor="mm")
        return out


# =========================================================================== KI-Scan

class AIScan(Effect):
    """KI-Analyse: Scan-Linie fährt über die Person, Punktraster, Klammern fixieren den Kopf, Daten tippen sich ein."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.3, 0.35)
        if pin <= 0:
            return frame
        rel, dur = t - self.at, max(1.0, self.until - self.at)
        m = person_mask(frame, t)
        acc = rgba(self.cfg.get("color", "#3DF5C8"))
        mono = lambda s: font_named("CourierPrime-Bold.ttf", s)
        out = frame.convert("RGB")
        # leicht entsättigen + abdunkeln
        out = Image.blend(out, ImageOps.grayscale(out).convert("RGB"), 0.35 * pout)
        out = Image.blend(out, Image.new("RGB", (W, H), (4, 10, 12)), 0.25 * pout)
        sp = ease_in_out(clamp(rel / (dur * 0.45)))
        sy = int(H * sp)
        # Punktraster auf der Person oberhalb der Scanlinie
        grid = np.zeros((H, W), np.float32)
        grid[::14, ::14] = 1
        grid = np.asarray(Image.fromarray((grid * 255).astype("uint8")).filter(ImageFilter.MaxFilter(3)), np.float32) / 255
        pm = np.asarray(m, np.float32) / 255
        above = np.zeros((H, 1), np.float32)
        above[:sy] = 1
        fade = clamp(1 - (rel - dur * 0.55) / (dur * 0.3))
        dots = grid * pm * above * 0.85 * fade * pout
        light = dots[..., None] * np.array(acc[:3], np.float32)
        band = np.exp(-((np.arange(H) - sy) / 26.0) ** 2)[:, None] * (0.9 if sp < 1 else 0) * pout
        light += band[..., None] * np.array(acc[:3], np.float32) * 0.9
        light += (band * pm)[..., None] * 140
        out = additive(out, light).convert("RGBA")
        d = ImageDraw.Draw(out)
        # Klammern um den Kopf
        hx0, hy0, hx1, hy1 = head_box(m)
        lp = ease_out_cubic(clamp((rel - 0.2) / 0.6))
        bx0, by0 = 40 + (hx0 - 30 - 40) * lp, 120 + (hy0 - 30 - 120) * lp
        bx1, by1 = W - 40 + (hx1 + 30 - W + 40) * lp, H * 0.8 + (hy1 + 20 - H * 0.8) * lp
        L = 56
        col = acc[:3] + (int(255 * pout),)
        for (x, y, dx, dy) in [(bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)]:
            d.line((x, y, x + dx * L, y), fill=col, width=6)
            d.line((x, y, x, y + dy * L), fill=col, width=6)
        if lp > 0.98:
            d.text((bx0, by0 - 40), "ZIEL ERFASST", font=mono(28), fill=col)
        # Datenzeilen tippen sich ein
        lines = self.cfg.get("zeilen", ["PERSON ERKANNT", "ANALYSE ... 98 %", "MODUS: KI-CREATOR"])
        tx = bx1 + 26 if bx1 + 26 < W - 330 else max(40, bx0 - 360)
        ty = by0 + 20
        for k, ln in enumerate(lines):
            st = 0.6 + 0.45 * k
            if rel < st:
                break
            n = int(clamp((rel - st) / 0.4) * len(ln))
            txt = ln[:n] + ("_" if n < len(ln) and int(t * 6) % 2 else "")
            f = mono(30)
            tw_ = text_size(ln, f)[0]
            d.rectangle((tx - 10, ty - 6, tx + tw_ + 14, ty + 40), fill=(0, 0, 0, int(150 * pout)))
            d.text((tx, ty), txt, font=f, fill=col)
            ty += 58
        # Radar unten links
        r = 70
        cx_, cy_ = 130, H - 260
        d.ellipse((cx_ - r, cy_ - r, cx_ + r, cy_ + r), outline=col, width=3)
        d.ellipse((cx_ - r / 2, cy_ - r / 2, cx_ + r / 2, cy_ + r / 2), outline=acc[:3] + (int(120 * pout),), width=2)
        an = t * 4
        d.line((cx_, cy_, cx_ + r * math.cos(an), cy_ + r * math.sin(an)), fill=col, width=4)
        flash = clamp(1 - abs(rel - dur * 0.85) / 0.08) * 0.5
        if flash > 0:
            out = Image.blend(out, Image.new("RGBA", (W, H), acc[:3] + (255,)), flash)
        return out


# =========================================================================== Handy-Portal

class PhonePortal(Effect):
    """Das Video schrumpft in ein schwebendes iPhone, kippt in 3D – und zoomt wieder auf Vollbild."""

    def covers(self, t):
        return self.at + 0.2 <= t <= self.until - 0.2

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        tr = float(self.cfg.get("uebergang", 0.5))
        pi_ = ease_in_out(clamp((t - self.at) / tr))
        po_ = ease_in_out(clamp((t - (self.until - tr)) / tr))
        s = pi_ * (1 - po_)
        if s < 0.003:
            return frame
        if self.cfg.get("media") and not hasattr(self, "_media"):
            from effects import MediaReader
            self._media = MediaReader(self.cfg["media"], (W, H))
        content = self._media.get(t - self.at) if hasattr(self, "_media") else frame
        content = content if content is not None else frame
        bg = frame.filter(ImageFilter.GaussianBlur(30))
        bg = Image.blend(bg, Image.new("RGB", (W, H), (6, 4, 14)), 0.55 * s)
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        acc = rgba(self.brand["accent"])
        ImageDraw.Draw(glow).ellipse((W * 0.1, H * 0.2, W * 0.9, H * 0.8), fill=acc[:3] + (int(120 * s),))
        bg = Image.alpha_composite(bg.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(120)))
        k = 1 - 0.40 * s
        sw_, sh_ = int(W * k), int(H * k)
        rad = int(80 * s)
        bez = int(20 * s) + 1
        ph = Image.new("RGBA", (sw_ + 2 * bez, sh_ + 2 * bez), (0, 0, 0, 0))
        d = ImageDraw.Draw(ph)
        d.rounded_rectangle((0, 0, ph.width - 1, ph.height - 1), rad + bez, fill=(14, 14, 16, 255), outline=(70, 70, 76, 255), width=3)
        scr = content.convert("RGB").resize((sw_, sh_), Image.LANCZOS)
        mk = Image.new("L", (sw_, sh_), 0)
        ImageDraw.Draw(mk).rounded_rectangle((0, 0, sw_ - 1, sh_ - 1), rad, fill=255)
        ph.paste(scr, (bez, bez), mk)
        if s > 0.3:
            iw = int(sw_ * 0.28)
            d.rounded_rectangle((ph.width / 2 - iw / 2, bez + 18, ph.width / 2 + iw / 2, bez + 18 + iw * 0.28), iw * 0.14, fill=(0, 0, 0, 255))
        # Glanz
        sh = Image.new("RGBA", ph.size, (0, 0, 0, 0))
        gx = (t * 0.6 % 1.6 - 0.3) * ph.width
        ImageDraw.Draw(sh).polygon([(gx, 0), (gx + 140, 0), (gx - 260, ph.height), (gx - 400, ph.height)], fill=(255, 255, 255, int(28 * s)))
        ph = Image.alpha_composite(ph, Image.composite(sh, Image.new("RGBA", ph.size, (0, 0, 0, 0)), ph.getchannel("A")))
        # 3D-Kippen
        ang = s * float(self.cfg.get("kippen", 14)) * math.sin((t - self.at) * 1.3)
        a = math.radians(ang)
        w2, h2 = ph.width, ph.height
        shrink = abs(math.sin(a)) * 0.22
        dx = w2 * (1 - math.cos(a)) / 2
        if ang >= 0:
            dst = [(dx, 0), (w2 - dx, h2 * shrink), (w2 - dx, h2 * (1 - shrink)), (dx, h2)]
        else:
            dst = [(dx, h2 * shrink), (w2 - dx, 0), (w2 - dx, h2), (dx, h2 * (1 - shrink))]
        src = [(0, 0), (w2, 0), (w2, h2), (0, h2)]
        ph = ph.transform((w2, h2), Image.PERSPECTIVE, find_coeffs(dst, src), Image.BICUBIC)
        shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(((W - w2) / 2 + 30, (H - h2) / 2 + 60, (W + w2) / 2 + 30, (H + h2) / 2 + 60), rad, fill=(0, 0, 0, int(150 * s)))
        bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(40)))
        fy = math.sin((t - self.at) * 2) * 10 * s
        bg.alpha_composite(ph, (int((W - w2) / 2), int((H - h2) / 2 + fy)))
        txt = self.cfg.get("text")
        if txt and s > 0.6:
            el = text_img(clean_text(txt), font(58, 900), shadow_alpha=200, pad=16)
            paste_scaled(bg, el, W / 2, (H - h2) / 2 - 70 + fy, 1.0, clamp((s - 0.6) / 0.4))
        return bg


# =========================================================================== Spotlight

class Spotlight(Effect):
    """Kino-Look: Hintergrund wird zweifarbig (Duotone) mit drehenden Lichtstrahlen, die Person bleibt in Farbe und bekommt Randlicht."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.5, 0.4)
        if pin <= 0:
            return frame
        m = person_mask(frame, t)
        a = ease_out_cubic(pin) * pout
        dark = rgba(self.cfg.get("dunkel", "#0A0614"))[:3]
        light = rgba(self.cfg.get("hell", self.brand["accent2"]))[:3]
        bgd = duotone(frame, dark, light)
        if not hasattr(self, "_rays"):
            n = 2200
            Y, X = np.mgrid[0:n // 2, 0:n // 2].astype(np.float32)
            ang = np.arctan2(Y - n / 4, X - n / 4)
            rng = np.random.default_rng(3)
            ray = np.zeros_like(ang)
            for _ in range(18):
                c, wd = rng.uniform(-math.pi, math.pi), rng.uniform(0.03, 0.09)
                ray += np.exp(-(((ang - c + math.pi) % (2 * math.pi) - math.pi) / wd) ** 2)
            r = np.hypot(Y - n / 4, X - n / 4) / (n / 4)
            ray *= np.clip(1.2 - r, 0, 1)
            self._rays = Image.fromarray((np.clip(ray, 0, 1) * 255).astype("uint8"))
        rays = self._rays.rotate(t * 6, resample=Image.BILINEAR)
        cx, cy = float(self.cfg.get("cx", 0.5)) * W, float(self.cfg.get("cy", 0.3)) * H
        rl = Image.new("L", (W, H), 0)
        rl.paste(rays, (int(cx - rays.width / 2), int(cy - rays.height / 2)))
        rl = rl.filter(ImageFilter.GaussianBlur(6))
        base = Image.blend(frame.convert("RGB"), bgd, a)
        ra = np.asarray(rl, np.float32)[..., None] / 255 * 0.55 * a
        base = additive(base, ra * np.array([255, 255, 255], np.float32) * 0.6 + ra * np.array(light, np.float32) * 0.6)
        # Vignette
        Y, X = np.ogrid[0:H, 0:W]
        vig = 1 - 0.55 * a * np.clip(np.hypot((X - W / 2) / (W * 0.75), (Y - H * 0.45) / (H * 0.6)), 0, 1)[..., None] ** 2
        base = Image.fromarray(np.clip(np.asarray(base, np.float32) * vig, 0, 255).astype("uint8"))
        out = base.convert("RGBA")
        out.paste(frame.convert("RGBA"), (0, 0), m)
        # Randlicht
        half = m.resize((W // 2, H // 2))
        edge = ImageChops.subtract(half.filter(ImageFilter.MaxFilter(7)), half).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10))
        rim = np.asarray(edge, np.float32)[..., None] / 255 * a
        out = additive(out, rim * (np.array(light, np.float32) * 1.4 + 60)).convert("RGBA")
        return out


# =========================================================================== Registry-Ergänzung

PRO = {
    "neon-kontur": NeonContour,
    "klon-echo": CloneEcho,
    "freeze-sticker": FreezeSticker,
    "magazin-cover": MagazineCover,
    "ki-scan": AIScan,
    "handy-portal": PhonePortal,
    "spotlight": Spotlight,
}


# =========================================================================== App-Logos

from pathlib import Path as _P

LOGO_DIR = _P(__file__).resolve().parent / "logos"
LOGO_ALIAS = {"kalender": "googlecalendar", "google kalender": "googlecalendar", "google calendar": "googlecalendar",
              "chatgpt": "openai", "meet": "googlemeet", "google meet": "googlemeet", "twitter": "x", "fb": "facebook",
              "wa": "whatsapp", "mail": "gmail", "e-mail": "gmail"}


def app_logo(name, size=64):
    """Echtes App-Logo (iOS-Icon-Stil) aus logos/, sonst None."""
    key = (name or "").lower().strip()
    key = LOGO_ALIAS.get(key, key.replace(" ", ""))
    f = LOGO_DIR / f"{key}.png"
    if not f.exists():
        return None
    return Image.open(f).convert("RGBA").resize((size, size), Image.LANCZOS)


# =========================================================================== Beweis-Stapel (ersetzt die alte Beweis-Karte)

class ProofStack(Effect):
    """iPhone-Benachrichtigungen (Zahlung, Kunde, Follower …) stapeln sich neben dem Kopf, Kamera zoomt leicht heran."""

    layer = "both"

    def zoom(self, frame, t):
        pin, pout = window(t, self.at - 0.1, self.until, 0.6, 0.45)
        return zoom_frame(frame, 1 + float(self.cfg.get("zoom", 0.07)) * ease_in_out(pin) * pout, cy=0.38)

    def _card(self, c, w):
        h = 156
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, w - 1, h - 1), 38, fill=(245, 245, 247, 238))
        logo = app_logo(c.get("logo") or c.get("app"), 64)
        if logo is not None:
            img.alpha_composite(logo, (26, 30))
        else:
            col = rgba(c.get("farbe", self.brand["accent"]))
            d.rounded_rectangle((26, 30, 26 + 64, 30 + 64), 16, fill=col)
            d.text((58, 62), (c.get("app", "A")[:1]).upper(), font=font(36, 900), fill=(255, 255, 255, 255), anchor="mm")
        d.text((110, 30), c.get("app", "Stripe").upper(), font=font(22, 700), fill=(120, 120, 128, 255))
        d.text((w - 30, 30), c.get("zeit", "jetzt"), font=font(22, 500), fill=(140, 140, 148, 255), anchor="ra")
        d.text((110, 62), clean_text(c.get("titel", "Zahlung erhalten")), font=font(32, 800), fill=(16, 16, 18, 255))
        d.text((110, 104), clean_text(c.get("text", "+ 1.250,00 €")), font=font(30, 700), fill=rgba(c.get("textfarbe", "#1F9D55")))
        return img

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.3, 0.35)
        if pin <= 0:
            return frame
        cards = self.cfg.get("karten") or [
            {"app": "Stripe", "titel": "Zahlung erhalten", "text": "+ 1.250,00 €", "farbe": "#635BFF"},
            {"app": "Instagram", "titel": "Neue Follower", "text": "+ 2.400 heute", "farbe": "#E1306C", "textfarbe": "#E1306C"},
            {"app": "Kalender", "titel": "Neuer Termin", "text": "Erstgespräch · 14:00", "textfarbe": "#1A73E8"},
        ]
        step = float(self.cfg.get("abstand", 0.6))
        times = [float(c.get("at", self.at + 0.15 + i * step)) for i, c in enumerate(cards)]
        w = int(self.cfg.get("w", 640))
        x = float(self.cfg.get("x", 0.5)) * W
        y0 = float(self.cfg.get("y", 0.12)) * H
        orig = frame
        frame = frame.convert("RGBA")
        shown = [i for i, tt in enumerate(times) if t >= tt]
        gap = 18
        if not hasattr(self, "_ybase"):   # Stapel endet knapp über dem Kopf (leicht dahinter)
            self._ybase = float(self.cfg["y"]) * H if "y" in self.cfg else max(40, head_box(person_mask(orig, t))[1] - 156 + 40)
        for i in shown:                                     # neueste unten am Kopf, ältere rutschen nach oben
            newer = [j for j in shown if j > i]
            rel = t - times[i]
            s_in = spring(clamp(rel / 0.6), 6.5, 1.6)
            shift = sum(ease_out_cubic(clamp((t - times[j]) / 0.35)) for j in newer) * (156 + gap)
            yy = self._ybase - shift + (1 - clamp(s_in)) * 120
            fade = clamp((yy + 120) / 160)
            if fade <= 0:
                continue
            el = self._card(cards[i], w)
            sh = Image.new("RGBA", (el.width + 80, el.height + 80), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((40, 54, 40 + el.width, 54 + el.height), 38, fill=(0, 0, 0, 100))
            sh = sh.filter(ImageFilter.GaussianBlur(18))
            sh.alpha_composite(el, (40, 40))
            paste_scaled(frame, sh, x, yy + sh.height / 2, 0.85 + 0.15 * clamp(s_in), clamp(rel * 7) * pout * fade)
        if self.cfg.get("hinter_kopf", True):   # Karten liegen hinter der Person
            frame.paste(orig.convert("RGBA"), (0, 0), person_mask(orig, t))
        return frame


# =========================================================================== Pixel-Push (lesbar)

class PixelPushPro(Effect):
    """LED-Laufschrift: jedes Wort steht gut lesbar in der Mitte und wird schnell zum nächsten weitergeschoben."""

    def covers(self, t):
        return self.at <= t <= self.until

    def _prep(self):
        if self.cfg.get("words"):
            off = float(self.cfg.get("offset", 0))
            ws = [{"w": w["w"].strip(",."), "s": w["s"] - off} for w in load_words(self.cfg["words"]) if self.at + off - 0.05 <= w["s"] < self.until + off]
        else:
            toks = self.cfg.get("text", "Alles mit einem Prompt.").split()
            st = (self.until - self.at) / max(1, len(toks))
            ws = [{"w": w, "s": self.at + i * st} for i, w in enumerate(toks)]
        self.ws = ws or [{"w": "KI", "s": self.at}]
        longest = max(self.ws, key=lambda w: len(w["w"]))["w"].upper()
        size = 340
        while text_size(longest, font(size, 900))[0] > W * 0.86 and size > 120:
            size -= 10
        self.f = font(size, 900)
        cell = int(self.cfg.get("pixel", 7))
        self.cell = cell
        yy, xx = np.mgrid[0:H, 0:W]
        cx, cy = (xx % cell) - cell / 2 + 0.5, (yy % cell) - cell / 2 + 0.5
        dot = np.clip(1.35 - np.sqrt(cx ** 2 + cy ** 2) / (cell * 0.44), 0, 1)
        self.dot = dot.astype(np.float32)[..., None]

    def _word_img(self, word):
        txt = word.upper()
        tw, th = text_size(txt, self.f)
        l_, t_, _, _ = self.f.getbbox(txt)
        img = Image.new("L", (tw + 40, th + 40), 0)
        ImageDraw.Draw(img).text((20 - l_, 20 - t_), txt, font=self.f, fill=255)
        return img

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        if not hasattr(self, "ws"):
            self._prep()
        idx = max([i for i, w in enumerate(self.ws) if w["s"] <= t] or [0])
        p = ease_out_cubic(clamp((t - self.ws[idx]["s"]) / 0.16))   # Push dauert nur 0,16 s
        canvas = Image.new("L", (W, H), 0)
        cur = self._word_img(self.ws[idx]["w"])
        y = int(H * float(self.cfg.get("y", 0.5)) - cur.height / 2)
        canvas.paste(cur, (int((W - cur.width) / 2 + (1 - p) * W * 0.9), y))
        if idx > 0 and p < 1:
            prev = self._word_img(self.ws[idx - 1]["w"])
            canvas.paste(prev, (int((W - prev.width) / 2 - p * W * 0.9), y), prev)
        if p < 1:  # Bewegungsunschärfe während des Pushs
            canvas = canvas.filter(ImageFilter.BoxBlur(int(14 * (1 - p)) + 1))
        c = self.cell
        small = canvas.resize((W // c, H // c), Image.BOX).resize((W, H), Image.NEAREST)
        lum = np.asarray(small, np.float32)[..., None] / 255
        tint = np.array(rgba(self.cfg.get("color", "#F4F2EE"))[:3], np.float32)
        bg = np.array(rgba(self.cfg.get("bg", "#08080A"))[:3], np.float32)
        img = bg * (0.55 + 0.45 * self.dot) + lum * tint * 1.15 * self.dot
        out = Image.fromarray(np.clip(img, 0, 255).astype("uint8"))
        glow = np.asarray(out.filter(ImageFilter.GaussianBlur(12)), np.float32)
        out = Image.fromarray(np.clip(np.asarray(out, np.float32) + glow * 0.5, 0, 255).astype("uint8"))
        fade = clamp((t - self.at) / 0.1) * clamp((self.until - t) / 0.1)
        return Image.blend(frame.convert("RGB"), out, fade) if fade < 1 else out


# =========================================================================== Große Worte (kinetisch)

class BigWordsPro(Effect):
    """Kinetische Typo: Wörter knallen nacheinander rein und stapeln sich zu einem großen Satzblock; Schlüsselwörter in Akzent-Box."""

    def covers(self, t):
        return self.at <= t <= self.until

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        if not hasattr(self, "ws"):
            off = float(self.cfg.get("offset", 0))
            if self.cfg.get("words"):
                self.ws = [{"w": w["w"].strip(","), "s": w["s"] - off} for w in load_words(self.cfg["words"]) if self.at + off - 0.05 <= w["s"] < self.until + off]
            else:
                toks = self.cfg.get("text", "Jeden Tag ein neuer KI-Trick").split()
                st = (self.until - self.at) / max(1, len(toks))
                self.ws = [{"w": w, "s": self.at + i * st} for i, w in enumerate(toks)]
            self.bet = {w.lower().strip(".,!?") for w in self.cfg.get("betonen", [])}
            # Layout: Zeilen à max. 2 Wörter, Blöcke à 3 Zeilen
            self.lines, cur = [], []
            for i, w in enumerate(self.ws):
                cur.append(i)
                if len(cur) == 2 or len(w["w"]) > 9:
                    self.lines.append(cur); cur = []
            if cur:
                self.lines.append(cur)
        hg = self.cfg.get("hintergrund", "blur")
        if hg == "blur":
            bg = frame.filter(ImageFilter.GaussianBlur(26)).convert("RGBA")
            bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (0, 0, 0, 165)))
        else:
            bg = Image.new("RGBA", (W, H), rgba(self.brand["accent"] if hg == "marke" else "#0B0B0D"))
        idx = max([i for i, w in enumerate(self.ws) if w["s"] <= t] or [0])
        li = next(k for k, ln in enumerate(self.lines) if idx in ln)
        block = li // 3
        lines = self.lines[block * 3: block * 3 + 3]
        size = 150
        shake = (0, 0)
        y = H * 0.5 - len(lines) * size * 0.62
        for ln in lines:
            x = 80
            for i in ln:
                if i > idx:
                    continue
                w = self.ws[i]
                emph = w["w"].lower().strip(".,!?") in self.bet
                rel = t - w["s"]
                p = clamp(rel / 0.14)
                sc = 1 + 0.6 * (1 - ease_out_cubic(p))
                f = font_named("InstrumentSerif-400-italic.ttf", int(size * 1.2)) if emph else font(size, 900)
                txt = clean_text(w["w"].upper() if not emph else w["w"], Path_name(f))
                tw, th = text_size(txt, f)
                if x + tw > W - 60 and x > 80:
                    break
                if emph:
                    box = Image.new("RGBA", (tw + 50, th + 50), (0, 0, 0, 0))
                    ImageDraw.Draw(box).rounded_rectangle((0, 0, box.width - 1, box.height - 1), 18, fill=rgba(self.cfg.get("color", self.brand["accent"])))
                    l_, t_, _, _ = f.getbbox(txt)
                    ImageDraw.Draw(box).text((25 - l_, 25 - t_), txt, font=f, fill=(255, 255, 255, 255))
                    el = box.rotate(-3, resample=Image.BICUBIC, expand=True)
                else:
                    el = text_img(txt, f, fill=(255, 255, 255, 255) if i == idx else (225, 225, 230, 255), shadow_alpha=150, pad=14)
                if i == idx and rel < 0.12:
                    shake = (np.sin(t * 90) * 10 * (1 - p), np.cos(t * 77) * 8 * (1 - p))
                paste_scaled(bg, el, x + el.width / 2 - 14, y + size * 0.55, sc, clamp(p * 3))
                x += tw + 50
            y += size * 1.2
        if shake != (0, 0):
            bg = bg.transform(bg.size, Image.AFFINE, (1, 0, -shake[0], 0, 1, -shake[1]), resample=Image.BILINEAR)
        fade = clamp((t - self.at) / 0.1) * clamp((self.until - t) / 0.1)
        return Image.blend(frame.convert("RGBA"), bg, fade) if fade < 1 else bg


def Path_name(f):
    from pathlib import Path
    return Path(f.path).name


# =========================================================================== Text hinter dem Kopf (Buchstaben steigen auf)

class TextBehindPro(Effect):
    """Riesiges Wort hinter der Person: Buchstaben steigen gestaffelt hinter den Schultern auf, Farbverlauf und Glanzkante."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.9, 0.35)
        if pin <= 0:
            return frame
        m = person_mask(frame, t)
        txt = clean_text(self.cfg.get("text", "KI").upper())
        size = int(self.cfg.get("size", 0)) or 460
        f = font(size, 900)
        while text_size(txt, f)[0] > W * 0.94 and size > 80:
            size -= 12
            f = font(size, 900)
        if not hasattr(self, "_letters"):
            top = rgba(self.cfg.get("color", "#FFFFFF"))
            bot = rgba(self.cfg.get("color2", self.brand["accent2"]))
            letters, x = [], 0
            for ch in txt:
                cw, chh = text_size(ch, f)
                l_, t_, _, _ = f.getbbox(ch)
                mk = Image.new("L", (cw + 20, int(size * 1.1)), 0)
                ImageDraw.Draw(mk).text((10 - l_, 10 - t_), ch, font=f, fill=255)
                grad = Image.linear_gradient("L").resize(mk.size)
                col = Image.composite(Image.new("RGBA", mk.size, bot), Image.new("RGBA", mk.size, top), grad)
                col.putalpha(mk)
                letters.append((col, x))
                x += f.getlength(ch)
            self._letters, self._tw = letters, x
        hb = head_box(m)
        cy = float(self.cfg.get("y", 0)) * H if self.cfg.get("y") else hb[1] + size * 0.32
        x0 = (W - self._tw) / 2
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        n = len(self._letters)
        for k, (el, lx) in enumerate(self._letters):
            q = ease_out_back(clamp((t - self.at - 0.06 * k) / 0.55))
            dy = (1 - clamp(q)) * size * 0.9
            lay.alpha_composite(Image.fromarray(np.dstack([np.asarray(el)[..., :3], (np.asarray(el)[..., 3] * clamp(q * 1.5) * pout).astype("uint8")])),
                                (int(x0 + lx - 10), int(cy - size * 0.55 + dy + (1 - q) * 0)))
        glow = lay.filter(ImageFilter.GaussianBlur(26))
        out = frame.convert("RGBA")
        out = Image.alpha_composite(out, Image.fromarray(np.dstack([np.asarray(glow)[..., :3], (np.asarray(glow)[..., 3] * 0.6).astype("uint8")])))
        out = Image.alpha_composite(out, lay)
        out.paste(frame.convert("RGBA"), (0, 0), m)
        return out


# =========================================================================== Zoom-Durchschnitt (heftig)

class ZoomThroughPro(Effect):
    """Heftiger Übergang: Zoom IN das Gesicht mit Radial-Blur und RGB-Split, Blitz, danach Peitschen-Zoom heraus mit Wackler."""

    layer = "pre"

    def apply(self, frame, t):
        d_in, d_out = 0.32, 0.4
        cut = self.at
        if not (cut - d_in <= t <= cut + d_out):
            return frame
        zmax = float(self.cfg.get("zoom", 4.0))
        cx, cy = float(self.cfg.get("cx", 0.5)), float(self.cfg.get("cy", 0.36))
        if t < cut:
            p = clamp((t - (cut - d_in)) / d_in) ** 2.2
        else:
            q = clamp((t - cut) / d_out)
            p = (1 - ease_out_cubic(q)) * 0.55 - 0.08 * math.sin(q * math.pi) * (1 - q)
        z = max(1.0, 1 + (zmax - 1) * p)
        acc = np.zeros((H, W, 3), np.float32)
        n = 6 if p > 0.1 else 1
        for k in range(n):
            acc += np.asarray(zoom_frame(frame, z * (1 + 0.06 * k * p), cx, cy), np.float32)
        out = acc / n
        sp = int(28 * p)
        if sp:
            out[..., 0] = np.roll(out[..., 0], sp, axis=1)
            out[..., 2] = np.roll(out[..., 2], -sp, axis=1)
        img = Image.fromarray(np.clip(out, 0, 255).astype("uint8"))
        if t >= cut:
            q = clamp((t - cut) / d_out)
            sh = (1 - q) * 18
            img = img.transform(img.size, Image.AFFINE, (1, 0, math.sin(t * 80) * sh, 0, 1, math.cos(t * 67) * sh), resample=Image.BILINEAR)
            leak = Image.new("RGB", img.size, (255, 140, 60))
            img = Image.blend(img, leak, 0.18 * (1 - q))
        fl = clamp(1 - abs(t - cut) / 0.06)
        if fl > 0:
            img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), fl * 0.9)
        return img


PRO.update({
    "beweis-karte": ProofStack,
    "pixel-push": PixelPushPro,
    "grosse-worte": BigWordsPro,
    "text-hinter-kopf": TextBehindPro,
    "zoom-durchschnitt": ZoomThroughPro,
})
