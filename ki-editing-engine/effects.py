"""Alle Effekte der Reel-Skills.

Jeder Effekt ist eine Fabrik  make_<name>(cfg, brand) -> Effect.
Ein Effect hat .layer ("pre" = verändert das Bild selbst, z. B. Zoom;
"post" = legt etwas darüber) und .apply(frame, t) -> frame.
Zeiten (at/until) sind Sekunden relativ zum Start des Ausschnitts.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from reelkit import (FPS, H, W, card, clamp, ease_in_out, ease_out_back, ease_out_cubic, font, font_named, glass,
                     paste_scaled, rgba, shear, spring, text_size, window, zoom_frame, clean_text)


class Effect:
    layer = "post"

    def __init__(self, cfg: dict, brand: dict):
        self.cfg, self.brand = cfg, brand
        self.at = float(cfg.get("at", 0))
        self.until = float(cfg["until"]) if "until" in cfg else self.at + float(cfg.get("dur", 3.0))

    def apply(self, frame: Image.Image, t: float) -> Image.Image:  # pragma: no cover
        return frame

    def occupied(self, t: float):
        """Vertikaler Bereich (y0, y1) in Pixeln, den der Effekt gerade belegt – Untertitel weichen aus."""
        return None

    def covers(self, t: float) -> bool:
        """True, wenn der Effekt gerade den ganzen Screen füllt – dann keine Untertitel."""
        return False


# =========================================================================== Text-Helfer

def text_img(txt, f, fill=(255, 255, 255, 255), shadow=True, shadow_alpha=150, pad=30):
    txt = clean_text(txt, Path(f.path).name) or " "
    tw, th = text_size(txt, f)
    l, top, _, _ = f.getbbox(txt)
    img = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l, pad - top + 4), txt, font=f, fill=(0, 0, 0, shadow_alpha), stroke_width=max(1, f.size // 30), stroke_fill=(0, 0, 0, shadow_alpha))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(max(6, f.size // 9))))
    ImageDraw.Draw(img).text((pad - l, pad - top), txt, font=f, fill=fill)
    return img


def boxed_text_img(txt, f, fg, bg, padx=26, pady=14, radius=14):
    txt = clean_text(txt, Path(f.path).name) or " "
    tw, th = text_size(txt, f)
    l, top, _, _ = f.getbbox(txt)
    asc, desc = f.getmetrics()
    bh = asc + desc - top + 2 * pady - 6
    img = Image.new("RGBA", (tw + 2 * padx, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius, fill=bg)
    d.text((padx - l, pady - top - 3), txt, font=f, fill=fg)
    return img


# =========================================================================== Untertitel

def load_words(src):
    if isinstance(src, list):
        return src
    return json.loads(Path(src).read_text())


def chunk_words(words, max_words=3, max_chars=18, gap=0.45):
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(x["w"] for x in cur + [w])) > max_chars or w["s"] - cur[-1]["e"] > gap):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w["w"].endswith((".", "!", "?", ",")):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        end = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else c[-1]["e"] + 0.4
        out.append({"words": c, "s": c[0]["s"], "e": min(end, c[-1]["e"] + 0.6)})
    return out


class Captions(Effect):
    """Wort-für-Wort-Untertitel. Stile: brust (dezent, auf Brusthöhe), gross (fett, aktives Wort markiert)."""

    def __init__(self, cfg, brand):
        super().__init__(cfg, brand)
        words = load_words(cfg["words"])
        self.offset = float(cfg.get("offset", 0))  # Startzeit des Ausschnitts im Original
        self.style = cfg.get("style", "brust")
        self.y = float(cfg.get("y", 0.64 if self.style == "brust" else 0.70))
        mw = int(cfg.get("max_words", 3 if self.style == "brust" else 2))
        self.chunks = chunk_words(words, max_words=mw, max_chars=20 if self.style == "brust" else 16)
        self.hide = [(float(a), float(b)) for a, b in cfg.get("hide", [])]  # Zeitfenster ohne Untertitel
        self.size = int(cfg.get("size", 96 if self.style == "gross" else 62))
        self.betonen = {w.lower().strip(".,!?") for w in cfg.get("betonen", [])}

    def apply(self, frame, t):
        tt = t + self.offset
        if any(a <= t <= b for a, b in self.hide):
            return frame
        ch = next((c for c in self.chunks if c["s"] <= tt < c["e"]), None)
        if not ch:
            return frame
        f = font(self.size, 900 if self.style == "gross" else 800)
        pop = ease_out_back(clamp((tt - ch["s"]) / 0.16)) if self.style == "gross" else ease_out_cubic(clamp((tt - ch["s"]) / 0.12))
        if self.style == "brust":
            txt = " ".join(w["w"] for w in ch["words"])
            el = text_img(txt, f, shadow_alpha=170)
        elif self.style == "akzent":
            acc = rgba(self.cfg.get("color", self.brand["accent2"]))
            parts = []
            for w in ch["words"]:
                key = w["w"].lower().strip(".,!?")
                if key in self.betonen:
                    parts.append(text_img(w["w"], font_named("InstrumentSerif-400-italic.ttf", int(self.size * 1.18)), fill=acc, pad=10, shadow_alpha=150))
                elif any(c.isdigit() for c in w["w"]):
                    parts.append(text_img(w["w"], f, fill=acc, pad=10, shadow_alpha=170))
                else:
                    parts.append(text_img(w["w"], f, pad=10, shadow_alpha=170))
            gap = int(self.size * 0.12)
            el = Image.new("RGBA", (sum(p.width for p in parts) + gap * (len(parts) - 1), max(p.height for p in parts)), (0, 0, 0, 0))
            x = 0
            for p in parts:
                el.alpha_composite(p, (x, el.height - p.height - (0 if p.height == el.height else int(self.size * 0.04))))
                x += p.width + gap
        else:
            parts = []
            for w in ch["words"]:
                active = w["s"] <= tt < w["e"] + 0.05
                word = w["w"].upper()
                if active:
                    parts.append(boxed_text_img(word, f, (255, 255, 255, 255), rgba(self.brand["highlight"]), padx=18, pady=10))
                else:
                    parts.append(text_img(word, f, pad=10, shadow_alpha=180))
            gap = 14
            wsum = sum(p.width for p in parts) + gap * (len(parts) - 1)
            hmax = max(p.height for p in parts)
            el = Image.new("RGBA", (wsum, hmax), (0, 0, 0, 0))
            x = 0
            for p in parts:
                el.alpha_composite(p, (x, (hmax - p.height) // 2))
                x += p.width + gap
        if el.width > W - 80:
            k = (W - 80) / el.width
            el = el.resize((int(el.width * k), int(el.height * k)), Image.LANCZOS)
        scale = 0.9 + 0.1 * pop
        y = getattr(self, "y_override", None) or self.y * H
        for (a, b) in getattr(self, "avoid", []):
            if a - el.height / 2 - 20 < y < b + el.height / 2 + 20:
                y = a - el.height / 2 + 6 if a - el.height / 2 > 0.30 * H else b + el.height / 2 - 6
        frame = frame.convert("RGBA")
        paste_scaled(frame, el, W / 2, y, scale, clamp(pop * 1.4))
        return frame


# =========================================================================== Titel (oben)

class Title(Effect):
    """Zweizeiliger Titel oben: Zeile 1 weiß, Zeile 2 in einer Box (wie 'Make your videos / too sticky to skip')."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.3, 0.25)
        if pin <= 0:
            return frame
        lines = self.cfg.get("text", "Titel|Zweite Zeile").split("|")
        size = int(self.cfg.get("size", 74))
        f = font(size, 800)
        box_style = self.cfg.get("box", "weiss")  # weiss | marke
        fg, bg = ((18, 18, 20, 255), (255, 255, 255, 255)) if box_style == "weiss" else ((255, 255, 255, 255), rgba(self.brand["accent"]))
        y = self.cfg.get("y", 0.15) * H
        frame = frame.convert("RGBA")
        for k, line in enumerate(lines):
            p = ease_out_cubic(clamp(pin * 1.0 - k * 0.25)) * pout
            boxed = (k == len(lines) - 1 and len(lines) > 1) or self.cfg.get("all_boxed")
            if box_style == "ranking":
                fr = font(int(size * 1.05), 900)
                txt = line.upper()
                tw_, th_ = text_size(txt, fr)
                l_, t_, _, _ = fr.getbbox(txt)
                el = Image.new("RGBA", (tw_ + 40, th_ + 40), (0, 0, 0, 0))
                sh = Image.new("RGBA", el.size, (0, 0, 0, 0))
                ImageDraw.Draw(sh).text((20 - l_ + 3, 20 - t_ + 5), txt, font=fr, fill=(0, 0, 0, 170))
                el = Image.alpha_composite(el, sh.filter(ImageFilter.GaussianBlur(3)))
                ImageDraw.Draw(el).text((20 - l_, 20 - t_), txt, font=fr, fill=rgba(self.cfg.get("color", "#FF9F43")),
                                        stroke_width=2, stroke_fill=(60, 30, 10, 255))
                el = shear(el, 0.18)
            else:
                el = boxed_text_img(line, f, fg, bg) if boxed else text_img(line, f, shadow_alpha=160, pad=16)
            paste_scaled(frame, el, W / 2, y + k * (size * 1.18) + (1 - p) * 30, 1.0, p)
        return frame


# =========================================================================== Glas-Chart

class GlassChart(Effect):
    """Milchglas-Karte mit Kurve, die nach oben klettert, und hochzählender Zahl."""

    def occupied(self, t):
        if self.at <= t <= self.until + 0.3:
            return (self.cy - self.chh / 2, self.cy + self.chh / 2)

    def __init__(self, cfg, brand):
        super().__init__(cfg, brand)
        pts = cfg.get("points") or [0.08, 0.14, 0.12, 0.22, 0.30, 0.34, 0.52, 0.62, 0.78, 0.92]
        self.pts = [float(p) for p in pts]
        self.cw, self.chh = int(cfg.get("w", 860)), int(cfg.get("h", 440))
        self.cy = float(cfg.get("y", 0.66)) * H

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.45, 0.35)
        if pin <= 0:
            return frame
        a = ease_out_cubic(pin) * pout
        grow = ease_in_out(clamp((t - self.at - 0.25) / float(self.cfg.get("grow", 1.8))))
        cw, chh = self.cw, self.chh
        dy = (1 - a) * 60
        x0, y0 = (W - cw) / 2, self.cy - chh / 2 + dy
        frame = frame.convert("RGBA")
        if a > 0.02:
            base = frame.copy()
            glass(base, (x0, y0, x0 + cw, y0 + chh), radius=44, blur=18, tint=(10, 12, 14, 70), border=(255, 255, 255, 120))
            sheen = Image.new("RGBA", (cw, chh), (0, 0, 0, 0))
            sd = ImageDraw.Draw(sheen)
            for yy in range(int(chh * 0.45)):
                sd.line((0, yy, cw, yy), fill=(255, 255, 255, int(38 * (1 - yy / (chh * 0.45)))))
            m = Image.new("L", (cw, chh), 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, cw - 1, chh - 1), 44, fill=255)
            sheen.putalpha(Image.fromarray((np.asarray(sheen.getchannel("A"), dtype=np.float32) * np.asarray(m, dtype=np.float32) / 255).astype("uint8")))
            base.alpha_composite(sheen, (int(x0), int(y0)))
            frame = Image.blend(frame, base, a)
        lay = Image.new("RGBA", (cw, chh), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        label = self.cfg.get("label", "WACHSTUM").upper()
        d.text((44, 40), " ".join(label), font=font(26, 700), fill=(255, 255, 255, 170))
        val = float(self.cfg.get("value", 67))
        dec = int(self.cfg.get("decimals", 0))
        cur = val * grow
        num = f"{cur:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        vtxt = f"{self.cfg.get('prefix', '')}{num}"
        fv = font(84, 800)
        vw, _ = text_size(vtxt, fv)
        suf = self.cfg.get("suffix", "%")
        fs = font(44, 700)
        sw, _ = text_size(suf, fs)
        d.text((cw - 44 - sw - vw - 6, 22), vtxt, font=fv, fill=(255, 255, 255, 255))
        d.text((cw - 44 - sw, 52), suf, font=fs, fill=(255, 255, 255, 230))
        # Kurve
        gx0, gx1, gy0, gy1 = 44, cw - 44, 150, chh - 44
        n = len(self.pts)
        xy = [(gx0 + (gx1 - gx0) * i / (n - 1), gy1 - (gy1 - gy0) * p) for i, p in enumerate(self.pts)]
        # bis zum aktuellen Fortschritt interpolieren
        pos = grow * (n - 1)
        k = int(pos)
        vis = xy[: k + 1]
        if k < n - 1:
            fr = pos - k
            vis.append((xy[k][0] + (xy[k + 1][0] - xy[k][0]) * fr, xy[k][1] + (xy[k + 1][1] - xy[k][1]) * fr))
        col = rgba(self.cfg.get("color", self.brand["green"]))
        if len(vis) >= 2:
            fill = Image.new("RGBA", (cw, chh), (0, 0, 0, 0))
            ImageDraw.Draw(fill).polygon(vis + [(vis[-1][0], gy1), (vis[0][0], gy1)], fill=col[:3] + (70,))
            grad = Image.linear_gradient("L").resize((cw, chh)).point(lambda v: 255 - v)
            fill.putalpha(Image.fromarray((np.array(fill.getchannel("A"), dtype=np.float32) * np.array(grad, dtype=np.float32) / 255).astype("uint8")))
            lay = Image.alpha_composite(lay, fill)
            d = ImageDraw.Draw(lay)
            d.line(vis, fill=col, width=7, joint="curve")
            hx, hy = vis[-1]
            glow = Image.new("RGBA", (cw, chh), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse((hx - 26, hy - 26, hx + 26, hy + 26), fill=col[:3] + (120,))
            lay = Image.alpha_composite(lay, glow.filter(ImageFilter.GaussianBlur(10)))
            d = ImageDraw.Draw(lay)
            d.ellipse((hx - 12, hy - 12, hx + 12, hy + 12), fill=(255, 255, 255, 255), outline=col, width=5)
        if a < 0.999:
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
        frame.alpha_composite(lay, (int(x0), int(y0)))
        return frame


# =========================================================================== Schalter (iOS-Toggles)

class Toggles(Effect):
    """Einstellungs-Karte: Schalter springen nacheinander auf AN."""

    def __init__(self, cfg, brand):
        super().__init__(cfg, brand)
        self.items = cfg.get("items", ["Ein Prompt", "In Claude einfügen", "Fertiges Ergebnis"])
        step = float(cfg.get("step", 0.7))
        self.times = [float(x) for x in cfg.get("times", [self.at + 0.6 + i * step for i in range(len(self.items))])]
        if "until" not in cfg:
            self.until = self.times[-1] + 1.4

    def occupied(self, t):
        if self.at <= t <= self.until + 0.3:
            cy, ch = float(self.cfg.get("y", 0.64)) * H, 104 * len(self.items) + 24
            return (cy - ch / 2, cy + ch / 2)

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.4, 0.3)
        if pin <= 0:
            return frame
        a = pout * clamp(pin * 1.5)
        rowh, cw = 104, int(self.cfg.get("w", 700))
        ch = rowh * len(self.items) + 24
        img, pad = card(cw, ch, radius=38, fill=(255, 255, 255, 246))
        d = ImageDraw.Draw(img)
        on_col = rgba(self.cfg.get("color", "#34C759"))
        for k, item in enumerate(self.items):
            y = pad + 12 + k * rowh
            if k:
                d.line((pad + 36, y, pad + cw - 36, y), fill=(0, 0, 0, 22), width=2)
            p = spring(clamp((t - self.times[k]) / 0.9), damping=6, freq=1.4) if t >= self.times[k] else 0.0
            on = clamp(p)
            txt_a = int(255 * (0.42 + 0.58 * clamp((t - self.times[k] + 0.4) / 0.4)))
            d.text((pad + 40, y + rowh / 2), item, font=font(40, 700), fill=(18, 18, 20, txt_a), anchor="lm")
            tw_, th_ = 104, 62
            tx, ty = pad + cw - 40 - tw_, y + (rowh - th_) / 2
            off = (229, 229, 234)
            col = tuple(int(off[i] + (on_col[i] - off[i]) * on) for i in range(3)) + (255,)
            d.rounded_rectangle((tx, ty, tx + tw_, ty + th_), th_ / 2, fill=col)
            kx = tx + 4 + (tw_ - th_) * clamp(p, 0, 1.08)
            d.ellipse((kx + 1, ty + 7, kx + th_ - 7, ty + th_ - 1), fill=(0, 0, 0, 40))
            d.ellipse((kx, ty + 4, kx + th_ - 8, ty + th_ - 4), fill=(255, 255, 255, 255))
        scale = 0.86 + 0.14 * ease_out_back(clamp(pin))
        frame = frame.convert("RGBA")
        paste_scaled(frame, img, W / 2, float(self.cfg.get("y", 0.64)) * H, scale, a)
        return frame


# =========================================================================== Beweis-Karte

class ProofCard(Effect):
    """Weiße Karte landet neben dem Kopf (z. B. 'NACHHER 32.000 € pro Monat'), optional mit Punch-in-Zoom."""

    layer = "both"

    def zoom(self, frame, t):
        z = float(self.cfg.get("zoom", 1.07))
        if z <= 1.0:
            return frame
        pin, pout = window(t, self.at - 0.1, self.until, 0.5, 0.45)
        return zoom_frame(frame, 1 + (z - 1) * ease_in_out(pin) * pout, cy=0.38)

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.6, 0.3)
        if pin <= 0:
            return frame
        kicker = self.cfg.get("kicker", "NACHHER").upper()
        value = self.cfg.get("value", "32.000 €")
        sub = self.cfg.get("sub", "pro Monat")
        k = float(self.cfg.get("scale", 1.0))
        fk, fv, fs = font(int(18 * k), 800), font(int(58 * k), 900), font(int(22 * k), 700)
        vw, _ = text_size(value, fv)
        cw = int(max(230 * k, vw + 52 * k))
        ch = int((158 if sub else 128) * k)
        img, pad = card(cw, ch, radius=int(24 * k), fill=(255, 255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((pad + 26 * k, pad + 22 * k), " ".join(kicker), font=fk, fill=(140, 140, 148, 255))
        d.text((pad + 24 * k, pad + 46 * k), value, font=fv, fill=rgba(self.cfg.get("color", self.brand["accent"])))
        if sub:
            d.text((pad + 26 * k, pad + 116 * k), sub, font=fs, fill=(85, 85, 92, 255))
        rot = float(self.cfg.get("tilt", 3)) * (0.4 + 0.6 * (1 - ease_out_cubic(pin)))
        if abs(rot) > 0.05:
            img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
        s = spring(pin * 0.75, damping=6.5, freq=1.6)
        side = self.cfg.get("side", "rechts")
        cx = float(self.cfg.get("x", 0.74 if side == "rechts" else 0.26)) * W
        cy = float(self.cfg.get("y", 0.30)) * H
        frame = frame.convert("RGBA")
        paste_scaled(frame, img, cx, cy + (1 - clamp(s)) * 40, 0.55 + 0.45 * s, clamp(pin * 2) * pout)
        return frame


# =========================================================================== Hilfen für Bilder aus dem Clip

def clip_frames(cfg, n):
    """n Standbilder aus dem Eingangsvideo (für Karten/Handys, wenn keine Bilder angegeben sind)."""
    from preview import grab
    from reelkit import probe
    src = cfg.get("_input")
    if not src:
        return []
    dur = probe(src)["duration"] or 10
    return [grab(src, dur * (k + 0.5) / n) for k in range(n)]


def load_images(cfg, key="images", n=6):
    paths = cfg.get(key) or []
    imgs = []
    for p in paths:
        if not Path(p).is_file():
            continue
        if str(p).lower().endswith((".mp4", ".mov", ".m4v", ".webm")):
            from preview import grab
            imgs.append(grab(str(p), 1.2))
        else:
            imgs.append(Image.open(p).convert("RGB"))
    return imgs or clip_frames(cfg, n)


def phone_card(img: Image.Image | None, w=300, h=534, radius=36, label=None, brand=None):
    """Bild im Handy-/Reel-Format mit runden Ecken und dünnem Rand."""
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if img is not None:
        k = max(w / img.width, h / img.height)
        im = img.resize((int(img.width * k) + 1, int(img.height * k) + 1), Image.LANCZOS)
        im = im.crop(((im.width - w) // 2, (im.height - h) // 2, (im.width - w) // 2 + w, (im.height - h) // 2 + h))
    else:
        im = Image.linear_gradient("L").resize((w, h)).convert("RGB")
        im = Image.merge("RGB", [p.point(lambda v, c=c_: int(c * (0.4 + 0.6 * v / 255))) for p, c_ in zip(im.split(), rgba(brand["accent"])[:3])])
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    c.paste(im.convert("RGBA"), (0, 0), mask)
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius, outline=(255, 255, 255, 120), width=3)
    if label:
        d.text((w / 2, h - 40), label, font=font(30, 800), fill=(255, 255, 255, 255), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 120))
    return c


# =========================================================================== Profil-Karte (vor der Brust, für tiefen-ui)

def fmt_num(v, dec=0):
    return f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def profile_card(frame, cfg, brand, t, w=820):
    """Dunkle Kanal-Karte: Avatar, Name, Handle, Zahl, Button (wechselt z. B. von 'Folgen' auf 'Gefolgt')."""
    h = 118
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 22, fill=(18, 18, 22, 215), outline=(255, 255, 255, 30), width=2)
    av = cfg.get("_avatar")
    if av is not None:
        m = Image.new("L", (78, 78), 0)
        ImageDraw.Draw(m).ellipse((0, 0, 77, 77), fill=255)
        img.paste(av.resize((78, 78)), (20, 20), m)
    switched = t >= float(cfg.get("wechsel_at", 1e9))
    d.text((116, 22), cfg.get("name", "Luca Delfino"), font=font(30, 800), fill=(255, 255, 255, 255))
    d.text((116, 58), cfg.get("handle", "@lucaidelfino"), font=font(21, 500), fill=(170, 170, 178, 255))
    num = cfg.get("zahl_neu" if switched and cfg.get("zahl_neu") else "zahl", "23.000 Follower")
    d.text((116, 84), num, font=font(21, 700), fill=rgba(brand["green"]) if switched else (200, 200, 206, 255))
    btn = cfg.get("button_neu", "Gefolgt") if switched else cfg.get("button", "Folgen")
    fb = font(24, 800)
    bw = text_size(btn, fb)[0] + 44
    bx = w - bw - 22
    d.rounded_rectangle((bx, 36, bx + bw, 82), 23, fill=(60, 60, 66, 255) if switched else (255, 255, 255, 255))
    d.text((bx + bw / 2, 59), btn, font=fb, fill=(220, 220, 226, 255) if switched else (16, 16, 18, 255), anchor="mm")
    return img


# =========================================================================== Split-Grafiken (oben animiert)

class GraphicSource:
    """Animierte Grafik für die obere Split-Hälfte. typ: icon-grid | zahl."""

    def __init__(self, spec, size, brand):
        self.spec, self.size, self.brand = spec, size, brand

    def get(self, rel):
        w, h = self.size
        img = Image.new("RGB", (w, h), (8, 8, 10))
        typ = self.spec.get("typ", "icon-grid")
        acc = rgba(self.spec.get("color", self.brand["accent2"]))
        if typ == "icon-grid":
            n = int(self.spec.get("n", 3))
            hi = int(self.spec.get("highlight", (n * n) // 2))
            p = spring(clamp((rel - float(self.spec.get("at", 0.4))) / 0.8), 6, 1.3)
            cell = min(w, h) * 0.24
            glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gx = w / 2 + ((hi % n) - (n - 1) / 2) * cell
            gy = h / 2 + ((hi // n) - (n - 1) / 2) * cell
            r = cell * (1.6 + 0.15 * math.sin(rel * 3))
            ImageDraw.Draw(glow).ellipse((gx - r, gy - r, gx + r, gy + r), fill=acc[:3] + (int(120 * clamp(p)),))
            img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(cell * 0.6)))
            d = ImageDraw.Draw(img)
            for k in range(n * n):
                cx = w / 2 + ((k % n) - (n - 1) / 2) * cell
                cy = h / 2 + ((k // n) - (n - 1) / 2) * cell
                rr = cell * 0.36 * (1 + 0.12 * clamp(p) * (k == hi))
                col = tuple(int(110 + (acc[i] - 110) * clamp(p)) for i in range(3)) if k == hi else (98, 98, 104)
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col + (255,))
                hd = rr * 0.36   # Person-Icon: Kopf + Schultern
                ic = (225, 225, 230, 255) if k != hi else (255, 255, 255, 255)
                d.ellipse((cx - hd, cy - rr * 0.55, cx + hd, cy - rr * 0.55 + 2 * hd), fill=ic)
                d.chord((cx - rr * 0.62, cy + rr * 0.12, cx + rr * 0.62, cy + rr * 1.25), 180, 360, fill=ic)
            return img.convert("RGB")
        if typ == "zahl":
            v = float(self.spec.get("value", 100)) * ease_out_cubic(clamp(rel / float(self.spec.get("dauer", 1.2))))
            txt = f"{self.spec.get('prefix', '')}{fmt_num(v, int(self.spec.get('decimals', 0)))}{self.spec.get('suffix', '')}"
            d = ImageDraw.Draw(img)
            d.text((w / 2, h / 2 - 20), txt, font=font(int(h * 0.30), 900), fill=acc[:3], anchor="mm")
            if self.spec.get("label"):
                d.text((w / 2, h / 2 + h * 0.2), self.spec["label"], font=font(int(h * 0.075), 700), fill=(200, 200, 206), anchor="mm")
            return img
        return img


# =========================================================================== Preis-Tag (zählt hoch)

class PriceTag(Effect):
    """Weißes Preisschild mit Punkt, Zahl zählt hoch (z. B. 26 € → 398 € → 500 €)."""

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.4, 0.25)
        if pin <= 0:
            return frame
        vals = [float(v) for v in self.cfg.get("values", [self.cfg.get("value", 500)])]
        times = [float(x) for x in self.cfg.get("times", [self.at + i * 0.6 for i in range(len(vals))])]
        i = max([k for k, tt in enumerate(times) if tt <= t] or [0])
        prev = vals[i - 1] if i > 0 else vals[0] * 0.05
        v = prev + (vals[i] - prev) * ease_out_cubic(clamp((t - times[i]) / 0.45))
        txt = f"{self.cfg.get('prefix', '')}{fmt_num(v, int(self.cfg.get('decimals', 0)))}{self.cfg.get('suffix', ' €')}"
        f = font(int(self.cfg.get("size", 64)), 900)
        tw, th = text_size(txt, f)
        w, h = tw + 110, int(th + 54)
        img = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        poly = [(20 + 30, 20), (20 + w, 20), (20 + w, 20 + h), (20 + 30, 20 + h), (20, 20 + h / 2)]
        ImageDraw.Draw(sh).polygon([(x + 4, y + 8) for x, y in poly], fill=(0, 0, 0, 90))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(8)))
        d = ImageDraw.Draw(img)
        d.polygon(poly, fill=(255, 255, 255, 255))
        d.ellipse((20 + 22, 20 + h / 2 - 7, 20 + 36, 20 + h / 2 + 7), fill=(30, 30, 34, 255))
        l_, t_, _, _ = f.getbbox(txt)
        d.text((20 + 62 - l_, 20 + (h - th) / 2 - t_), txt, font=f, fill=(18, 18, 20, 255))
        img = img.rotate(float(self.cfg.get("tilt", 6)), resample=Image.BICUBIC, expand=True)
        bump = 1 + 0.08 * (1 - clamp((t - times[i]) / 0.25)) if t >= times[i] else 1
        s = spring(pin * 0.8, 6.5, 1.6)
        frame = frame.convert("RGBA")
        paste_scaled(frame, img, float(self.cfg.get("x", 0.68)) * W, float(self.cfg.get("y", 0.2)) * H, (0.6 + 0.4 * s) * bump, clamp(pin * 2) * pout)
        return frame


# =========================================================================== Tiefen-UI (hinter dem Kopf)

class DepthUI(Effect):
    """UI-Elemente erscheinen HINTER der Person (Person wird freigestellt).
    style: 'faecher' = Reel-Karten im Fächer, 'panel' = großes App-Fenster mit Titel."""

    _seg = None

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.55, 0.35)
        if pin <= 0:
            return frame
        if DepthUI._seg is None:
            from segment import Segmenter
            DepthUI._seg = Segmenter(self.cfg.get("quality", "fast"))
        if not hasattr(self, "cards"):
            self._prepare()
        base = frame.convert("RGBA")
        lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        style = self.cfg.get("style", "faecher")
        cy = float(self.cfg.get("y", 0.36 if style == "faecher" else 0.26)) * H
        front = Image.new("RGBA", base.size, (0, 0, 0, 0))
        if style == "faecher":
            n = len(self.cards)
            vids = getattr(self, "_vids", {})
            labels = self.cfg.get("labels", [])
            spread = float(self.cfg.get("spreizung", 390))
            for k, c in enumerate(self.cards):
                if k in vids:   # Reel spielt in der Karte
                    fr = vids[k].get(t - self.at)
                    if fr is not None:
                        c = phone_card(fr, label=labels[k] if k < len(labels) else None, brand=self.brand)
                rel = (k - (n - 1) / 2) / max(1, (n - 1) / 2)       # -1 .. 1
                p = spring(clamp(pin * 1.1 - abs(rel) * 0.12), damping=6, freq=1.3)
                ang = -rel * 16 * p
                x = W / 2 + rel * spread * p
                y = cy + abs(rel) ** 2 * 120 * p + math.sin(t * 1.6 + k) * 6
                el = c.rotate(ang, resample=Image.BICUBIC, expand=True)
                vorne = self.cfg.get("vorne", False) and abs(rel) > 0.55
                if vorne:
                    y += float(self.cfg.get("vorne_tiefer", 260))
                paste_scaled(front if vorne else lay, el, x, y, (0.6 + 0.4 * clamp(p)) * (1.08 if vorne else 1), pout)
        elif style == "website":  # Browserfenster, Seite scrollt (Bildschirmaufnahme)
            p = ease_out_back(clamp(pin))
            panel = self._browser(t)
            ang = float(self.cfg.get("kippen", 0))
            if ang:
                panel = panel.rotate(ang, resample=Image.BICUBIC, expand=True)
            paste_scaled(lay, panel, W / 2, cy + (1 - p) * 90 + math.sin(t * 1.3) * 5, 0.84 + 0.16 * p, clamp(pin * 1.6) * pout)
        else:  # panel
            p = ease_out_back(clamp(pin))
            paste_scaled(lay, self.panel, W / 2, cy + (1 - p) * 80 + math.sin(t * 1.4) * 4, 0.86 + 0.14 * p, clamp(pin * 1.6) * pout)
        out = Image.alpha_composite(base, lay)
        person = self._seg.mask(frame, t)
        out.paste(frame.convert("RGBA"), (0, 0), person)  # Person wieder nach vorne
        out = Image.alpha_composite(out, front)            # äußere Karten vor der Person
        prof = self.cfg.get("profil")
        if prof:  # Kanal-Karte VOR der Person, auf Brusthöhe
            if "_avatar" not in prof:
                fx = frame.crop((int(W * 0.3), int(H * 0.12), int(W * 0.7), int(H * 0.12 + W * 0.4)))
                prof["_avatar"] = fx.convert("RGB")
            pc = profile_card(frame, prof, self.brand, t)
            pp = ease_out_back(clamp((pin - 0.2) * 1.4))
            paste_scaled(out, pc, W / 2, float(prof.get("y", 0.70)) * H + (1 - clamp(pp)) * 60, 0.9 + 0.1 * pp, clamp(pp * 1.5) * pout)
        return out

    def occupied(self, t):
        prof = self.cfg.get("profil")
        if prof and self.at <= t <= self.until + 0.3:
            y = float(prof.get("y", 0.70)) * H
            return (y - 60, y + 60)

    def _browser(self, t):
        """macOS-Browserfenster mit laufender Bildschirmaufnahme."""
        bw = int(self.cfg.get("w", 1000))
        if not hasattr(self, "_web"):
            from preview import grab as _g
            import subprocess as _sp
            src = self.cfg["media"]
            first = Image.open(src) if str(src).lower().endswith((".png", ".jpg")) else None
            from reelkit import probe as _pr
            # Seitenverhältnis der Aufnahme bestimmen
            out = _sp.run([__import__("reelkit").ffmpeg_bin(), "-hide_banner", "-i", src], capture_output=True, text=True).stderr
            import re as _re
            m = _re.search(r", (\d{3,5})x(\d{3,5})", out)
            ar = int(m[1]) / int(m[2]) if m else 16 / 10
            self._vh = int(bw / ar)
            self._web = MediaReader(src, (bw, self._vh), 0.0)
        bar = 64
        img = Image.new("RGBA", (bw + 120, self._vh + bar + 120), (0, 0, 0, 0))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((60, 80, 60 + bw, 80 + self._vh + bar), 26, fill=(0, 0, 0, 150))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(28)))
        win = Image.new("RGBA", (bw, self._vh + bar), (0, 0, 0, 0))
        d = ImageDraw.Draw(win)
        d.rounded_rectangle((0, 0, bw - 1, self._vh + bar - 1), 22, fill=(246, 246, 247, 255))
        for k, c in enumerate([(255, 95, 87), (255, 189, 46), (40, 200, 64)]):
            d.ellipse((22 + k * 30, 22, 42 + k * 30, 42), fill=c)
        d.rounded_rectangle((bw * 0.28, 14, bw * 0.72, 50), 12, fill=(229, 229, 233, 255))
        d.text((bw / 2, 32), self.cfg.get("url", "skims.com"), font=font(24, 600), fill=(60, 60, 66, 255), anchor="mm")
        fr = self._web.get(max(0.0, (t - self.at) * float(self.cfg.get("tempo", 1.0))))
        if fr is not None:
            m = Image.new("L", (bw, self._vh), 0)
            ImageDraw.Draw(m).rounded_rectangle((0, -30, bw - 1, self._vh - 1), 22, fill=255)
            win.paste(fr, (0, bar), m)
        img.alpha_composite(win, (60, 60))
        return img

    def _prepare(self):
        style = self.cfg.get("style", "faecher")
        if style == "faecher":
            paths = self.cfg.get("images") or []
            VID = (".mp4", ".mov", ".m4v", ".webm")
            self._vids = {k: MediaReader(p, (300, 534)) for k, p in enumerate(paths) if str(p).lower().endswith(VID) and Path(p).is_file()}
            stills = {k: Image.open(p).convert("RGB") for k, p in enumerate(paths) if not str(p).lower().endswith(VID) and Path(p).is_file()}
            imgs = [stills.get(k) or (self._vids[k].get(0.0) if k in self._vids else None) for k in range(len(paths))] if paths else load_images(self.cfg, n=int(self.cfg.get("count", 5)))
            imgs = [i for i in imgs if i is not None] or load_images(self.cfg, n=5)
            labels = self.cfg.get("labels", [])
            n = int(self.cfg.get("count", max(5, len(paths) or len(imgs))))
            self.cards = [phone_card(imgs[k % len(imgs)] if imgs else None, label=labels[k] if k < len(labels) else None, brand=self.brand) for k in range(n)]
        else:
            self.cards = []
            pw, ph = int(self.cfg.get("w", 920)), int(self.cfg.get("h", 820))
            img, pad = card(pw, ph, radius=34, fill=(14, 14, 18, 240), border=(255, 255, 255, 40))
            d = ImageDraw.Draw(img)
            d.text((pad + 44, pad + 36), self.cfg.get("app", "YouTube"), font=font(34, 800), fill=(255, 255, 255, 255))
            tabs = self.cfg.get("tabs", ["Start", "Videos", "Shorts"])
            x = pad + 44
            for k, tab in enumerate(tabs):
                d.text((x, pad + 100), tab, font=font(28, 700), fill=(255, 255, 255, 255 if k == 1 else 140))
                x += text_size(tab, font(28, 700))[0] + 36
            imgs = load_images(self.cfg, n=9)
            tw_ = (pw - 88 - 2 * 20) // 3
            th_ = int(tw_ * 0.62)
            rows = max(1, (ph - 170) // (th_ + 20))
            for k in range(3 * rows):
                cx, cy = pad + 44 + (k % 3) * (tw_ + 20), pad + 160 + (k // 3) * (th_ + 20)
                thumb = phone_card(imgs[k % len(imgs)] if imgs else None, w=tw_, h=th_, radius=14, brand=self.brand)
                img.alpha_composite(thumb, (int(cx), int(cy)))
            self.panel = img


# =========================================================================== Artikel-Schnitt (Wort bleibt stehen)

ARTICLE_TEXT = ("Früher haben Creator ganze Wochenenden damit verbracht, Rohmaterial zu schneiden. Heute denken Agenturen "
                "neu darüber nach, was ein Schnitt überhaupt ist. Frühe Nutzer beschrieben das Gefühl als ungewohnt, dann als "
                "unverzichtbar. Die Werkzeuge dahinter lesen jedes Wort, schneiden die Pausen heraus und setzen Effekte genau "
                "auf den Takt der Sprache. Wer einmal so gearbeitet hat, will nicht mehr zurück. ")

ARTICLE_STYLES = [  # Hintergrund, Textfarbe, Schrift, Größe
    ((16, 16, 18), (196, 196, 200), "DMSans-700.ttf", 74),
    ((238, 233, 222), (40, 36, 32), "InstrumentSerif-400.ttf", 96),
    ((244, 242, 238), (60, 60, 62), "CourierPrime-Regular.ttf", 70),
    ((250, 250, 248), (30, 30, 34), "DMSans-500.ttf", 72),
    ((28, 24, 22), (214, 206, 196), "InstrumentSerif-400.ttf", 92),
]


class WordZoom(Effect):
    """Schnelle Schnitte durch verschiedene Artikel – das Schlüsselwort bleibt immer an derselben Stelle stehen."""

    def covers(self, t):
        return self.at <= t <= self.until

    def _pages(self):
        word = self.cfg.get("word", "Claude")
        txt = (self.cfg.get("text") or ARTICLE_TEXT) * 4
        n = int(self.cfg.get("pages", 4))
        col = rgba(self.cfg.get("color", "#D62F2F"))
        self.pages = []
        for k in range(n):
            bg, fg, fname, size = ARTICLE_STYLES[k % len(ARTICLE_STYLES)]
            pw, ph = int(W * 1.35), int(H * 1.35)
            page = Image.new("RGB", (pw, ph), bg)
            d = ImageDraw.Draw(page)
            f = font_named(fname, size)
            lh = int(size * 1.32)
            words = txt.split()[k * 7:]
            cy = ph // 2
            first_y = cy - (cy // lh) * lh
            y, i = first_y - lh // 2, 0
            while y < ph:
                if abs(y + lh / 2 - cy) < lh / 2:  # Zeile mit dem Schlüsselwort
                    fw = font_named("DMSans-800.ttf", int(size * 1.45)) if k % 2 == 0 else font_named("CourierPrime-Bold.ttf", int(size * 1.5))
                    tw, th = text_size(word, fw)
                    bx0, by0 = pw / 2 - tw / 2 - 30, cy - th / 2 - 26
                    left = " ".join(words[i:i + 4]); right = " ".join(words[i + 4:i + 8]); i += 8
                    d.text((bx0 - 24, cy), left, font=f, fill=fg, anchor="rm")
                    d.text((bx0 + tw + 84, cy), right, font=f, fill=fg, anchor="lm")
                    sh = Image.new("RGBA", page.size, (0, 0, 0, 0))
                    ImageDraw.Draw(sh).rounded_rectangle((bx0 + 6, by0 + 12, bx0 + tw + 66, by0 + th + 64), 10, fill=(0, 0, 0, 110))
                    page.paste(sh.filter(ImageFilter.GaussianBlur(14)), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
                    d.rounded_rectangle((bx0, by0, bx0 + tw + 60, by0 + th + 52), 10, fill=col)
                    l_, t_, _, _ = fw.getbbox(word)
                    d.text((bx0 + 30 - l_, by0 + 26 - t_), word, font=fw, fill=(255, 255, 255))
                    y += lh
                    continue
                line = ""
                while i < len(words) and text_size((line + " " + words[i]).strip(), f)[0] < pw - 60:
                    line = (line + " " + words[i]).strip(); i += 1
                d.text((-40 if k % 2 else 30, y), line, font=f, fill=fg)
                y += lh
            self.pages.append(page)

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        if not hasattr(self, "pages"):
            self._pages()
        rel = t - self.at
        cut = float(self.cfg.get("cut", 0.32))                   # Sekunden pro Artikel
        k = min(int(rel / cut), len(self.pages) - 1) if self.cfg.get("stop_last", True) else int(rel / cut) % len(self.pages)
        page = self.pages[k]
        z = 1.0 + 0.10 * ease_out_cubic(rel / max(0.5, self.until - self.at))   # langsamer Push-in
        cw, ch = page.width / 1.35 / z, page.height / 1.35 / z
        cx, cy = page.width / 2, page.height / 2
        view = page.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.LANCZOS)
        # Tiefenunschärfe oben/unten, Wortzeile scharf
        blur = view.filter(ImageFilter.GaussianBlur(9))
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle((0, H / 2 - 170, W, H / 2 + 170), fill=255)
        blur.paste(view, (0, 0), m.filter(ImageFilter.GaussianBlur(70)))
        return blur


# =========================================================================== Pixel-Push (LED-Laufschrift)

class PixelPush(Effect):
    """Gesprochene Wörter laufen als riesige LED-Pixelschrift durch den Screen (synchron zum Transkript)."""

    def covers(self, t):
        return self.at <= t <= self.until

    def _prepare(self):
        words = []
        if self.cfg.get("words"):
            off = float(self.cfg.get("offset", 0))
            words = [w for w in load_words(self.cfg["words"]) if self.at + off - 0.05 <= w["s"] < self.until + off]
            words = [{"w": w["w"], "s": w["s"] - off} for w in words]
        if not words:  # fester Text, gleichmäßig verteilt
            toks = self.cfg.get("text", "Alles mit einem Prompt.").split()
            step = (self.until - self.at) / max(1, len(toks))
            words = [{"w": w, "s": self.at + i * step} for i, w in enumerate(toks)]
        size = int(self.cfg.get("size", 300))
        f = font(size, 900)
        gap = int(size * 0.32)
        widths = [text_size(w["w"], f)[0] for w in words]
        total = sum(widths) + gap * (len(words) + 1) + 2 * W
        strip = Image.new("L", (total, int(size * 1.5)), 0)
        d = ImageDraw.Draw(strip)
        x = W
        self.centers = []
        for w, wd in zip(words, widths):
            l_, t_, _, _ = f.getbbox(w["w"])
            d.text((x - l_, int(size * 0.25) - t_), w["w"], font=f, fill=255)
            self.centers.append((w["s"], x + wd / 2))
            x += wd + gap
        self.strip = strip
        cell = int(self.cfg.get("pixel", 9))
        self.cell = cell
        yy, xx = np.mgrid[0:H, 0:W]
        cx, cy = (xx % cell) - cell / 2 + 0.5, (yy % cell) - cell / 2 + 0.5
        dot = np.clip(1.25 - np.sqrt(cx ** 2 + cy ** 2) / (cell * 0.42), 0, 1)
        sub = (xx // max(1, cell // 3)) % 3                     # RGB-Subpixel-Streifen
        self.mask = np.stack([dot * (0.78 + 0.22 * (sub == c)) for c in range(3)], -1).astype(np.float32)
        self.scan = (0.82 + 0.18 * ((yy // 3) % 2)).astype(np.float32)[..., None]

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        if not hasattr(self, "strip"):
            self._prepare()
        # Position: das aktuelle Wort steht zu seinem Zeitpunkt in der Mitte, dazwischen gleitet die Schrift
        cs = self.centers
        if t <= cs[0][0]:
            xc = cs[0][1] - (cs[0][0] - t) * 900
        elif t >= cs[-1][0]:
            xc = cs[-1][1] + (t - cs[-1][0]) * 220
        else:
            i = max(j for j in range(len(cs)) if cs[j][0] <= t)
            j = min(i + 1, len(cs) - 1)
            p = (t - cs[i][0]) / max(0.01, cs[j][0] - cs[i][0]) if j != i else 0
            p = ease_in_out(clamp(p * 1.25))
            xc = cs[i][1] + (cs[j][1] - cs[i][1]) * p
        x0 = int(xc - W / 2)
        band = self.strip.crop((x0, 0, x0 + W, self.strip.height))
        txt = Image.new("L", (W, H), 0)
        txt.paste(band, (0, int(H * float(self.cfg.get("y", 0.5)) - self.strip.height / 2)))
        c = self.cell
        small = txt.resize((W // c, H // c), Image.BOX).resize((W, H), Image.NEAREST)
        lum = np.asarray(small, dtype=np.float32)[..., None] / 255.0
        tint = np.array(rgba(self.cfg.get("color", "#E8E6E3"))[:3], dtype=np.float32) / 255
        base = np.array(rgba(self.cfg.get("bg", "#0E0E10"))[:3], dtype=np.float32) / 255
        img = (base * 0.9 + lum * tint * 1.9) * self.mask * self.scan + base * 0.35
        out = Image.fromarray((np.clip(img, 0, 1) * 255).astype("uint8"))
        glow = np.asarray(out.filter(ImageFilter.GaussianBlur(14)), dtype=np.float32)
        out = Image.fromarray(np.clip(np.asarray(out, dtype=np.float32) + glow * 0.55, 0, 255).astype("uint8"))
        fade = clamp((t - self.at) / 0.12) * clamp((self.until - t) / 0.12)
        return Image.blend(frame.convert("RGB"), out, fade) if fade < 1 else out


# =========================================================================== Glitch-Push

class GlitchPush(Effect):
    """Großer Text füllt den Screen; digitaler Übergang mit Streifen-Versatz und RGB-Split."""

    def covers(self, t):
        return self.at + 0.1 <= t <= self.until - 0.1

    def _panel(self):
        bg = rgba(self.cfg.get("bg", "#0B0B0F"))[:3]
        p = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(p)
        text = self.cfg.get("text", "Alles ändert sich.")
        size = int(self.cfg.get("size", 170))
        f = font(size, 900)
        lines, cur = [], ""
        for w in text.split():
            if text_size((cur + " " + w).strip(), f)[0] > W - 140:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        y = H / 2 - len(lines) * size * 0.55
        acc = rgba(self.cfg.get("color", self.brand["accent2"]))
        for k, ln in enumerate(lines):
            d.text((W / 2, y + k * size * 1.08), ln, font=f, fill=(255, 255, 255) if k < len(lines) - 1 or len(lines) == 1 else acc[:3], anchor="mt")
        for yy in range(0, H, 6):  # feine Scanlines
            d.line((0, yy, W, yy), fill=tuple(max(0, c - 6) for c in bg), width=2)
        self.panel = p

    @staticmethod
    def glitch(img: Image.Image, amount: float, seed: int) -> Image.Image:
        if amount <= 0.01:
            return img
        rng = np.random.default_rng(seed)
        a = np.asarray(img).copy()
        for _ in range(int(6 + 18 * amount)):
            y0 = int(rng.integers(0, H - 40))
            hgt = int(rng.integers(8, 90))
            shift = int(rng.integers(-1, 2) * rng.integers(20, 160) * amount)
            a[y0:y0 + hgt] = np.roll(a[y0:y0 + hgt], shift, axis=1)
        s = int(18 * amount)
        if s:
            a[..., 0] = np.roll(a[..., 0], s, axis=1)
            a[..., 2] = np.roll(a[..., 2], -s, axis=1)
        return Image.fromarray(a)

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        if not hasattr(self, "panel"):
            self._panel()
        tin, tout = 0.32, 0.28
        frame = frame.convert("RGB")
        if t < self.at + tin:  # Video wird nach oben weggeschoben
            p = ease_in_out((t - self.at) / tin)
            off = int(p * H)
            out = Image.new("RGB", (W, H))
            out.paste(frame, (0, -off))
            out.paste(self.panel, (0, H - off))
            return self.glitch(out, 1 - abs(p - 0.5) * 1.6, int(t * 1000))
        if t > self.until - tout:  # zurück zum Video
            p = ease_in_out((t - (self.until - tout)) / tout)
            off = int(p * H)
            out = Image.new("RGB", (W, H))
            out.paste(self.panel, (0, -off))
            out.paste(frame, (0, H - off))
            return self.glitch(out, 1 - abs(p - 0.5) * 1.6, int(t * 1000))
        jitter = 0.18 if int(t * 12) % 9 == 0 else 0.0
        return self.glitch(self.panel.copy(), jitter, int(t * 1000))


# =========================================================================== Tier-Liste (Karten fallen rein)

TIER_COLORS = {"S": "#FF7A7A", "A": "#FFB36B", "B": "#FFE066", "C": "#7BE495", "D": "#6EC6FF", "E": "#8C9EFF", "F": "#E879F9"}


def item_card(name, w, h, img=None, big=True):
    """Dunkle Karte mit Logo/Bild (optional) und Namen in Großbuchstaben."""
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grad = Image.linear_gradient("L").resize((w, h)).point(lambda v: int(18 + v * 0.10))
    base = Image.merge("RGB", [grad, grad, grad.point(lambda v: int(v * 1.9))])
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 12 if big else 8, fill=255)
    c.paste(base, (0, 0), m)
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 12 if big else 8, outline=(255, 255, 255, 200), width=4 if big else 2)
    if img is not None and (big or h > 120):
        k = min(w * 0.4 / img.width, h * 0.5 / img.height)
        im = img.convert("RGBA").resize((max(1, int(img.width * k)), max(1, int(img.height * k))))
        c.alpha_composite(im, ((w - im.width) // 2, int(h * 0.1)))
        f = font(int(h * 0.2), 900)
        txt = name.upper()
        while text_size(txt, f)[0] > w * 0.88 and f.size > 10:
            f = font(f.size - 2, 900)
        d.text((w / 2, h * 0.8), txt, font=f, fill=(255, 210, 60, 255) if big else (255, 255, 255, 255), anchor="mm")
        return c
    if img is not None:   # kleine Slot-Karte: Logo links, Name rechts
        ls = int(h * 0.74)
        im = img.convert("RGBA").resize((ls, ls), Image.LANCZOS)
        c.alpha_composite(im, (int(h * 0.13), (h - ls) // 2))
        f = font(int(h * 0.36), 900)
        txt = name.upper()
        while text_size(txt, f)[0] > w - ls - h * 0.45 and f.size > 8:
            f = font(f.size - 1, 900)
        d.text((ls + h * 0.3, h / 2), txt, font=f, fill=(255, 255, 255, 255), anchor="lm")
        return c
    f = font(int(h * (0.34 if big else 0.42)), 900)
    txt = name.upper()
    while text_size(txt, f)[0] > w * 0.88 and f.size > 10:
        f = font(f.size - 2, 900)
    d.text((w / 2, h * 0.52), txt, font=f, fill=(255, 210, 60, 255) if big else (255, 255, 255, 255), anchor="mm")
    return c


class TierList(Effect):
    """Ranking-Tabelle S–F; jedes Element erscheint groß und fällt dann in seine Reihe."""

    def occupied(self, t):
        if self.at <= t <= self.until + 0.3:
            cy = float(self.cfg.get("y", 0.66)) * H
            return (cy - self._h() / 2, cy + self._h() / 2)

    def _h(self):
        return 66 * len(self.cfg.get("tiers", list("SABCDEF")))

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.4, 0.3)
        if pin <= 0:
            return frame
        tiers = self.cfg.get("tiers", list("SABCDEF"))
        items = self.cfg.get("items", [])
        if not hasattr(self, "imgs"):
            from effects_pro import app_logo
            self.imgs = {}
            for it in items:
                if it.get("bild") and Path(it["bild"]).is_file():
                    self.imgs[it["name"]] = Image.open(it["bild"])
                else:
                    lg = app_logo(it.get("logo") or it["name"], 256)
                    if lg is not None:
                        self.imgs[it["name"]] = lg
        rowh, lab = 66, 58
        tw_, th_ = int(self.cfg.get("w", 820)), rowh * len(tiers)
        panel = Image.new("RGBA", (tw_, th_), (0, 0, 0, 0))
        d = ImageDraw.Draw(panel)
        d.rounded_rectangle((lab + 8, 0, tw_ - 1, th_ - 1), 18, fill=(12, 12, 16, 195), outline=(255, 255, 255, 70), width=2)
        for k, tier in enumerate(tiers):
            y = k * rowh
            c = rgba(TIER_COLORS.get(tier, "#999999"))
            lab_img = Image.new("RGBA", (lab, rowh - 6), c)
            gl = Image.linear_gradient("L").resize(lab_img.size).point(lambda v: int(90 - v * 0.35))
            white = Image.new("RGBA", lab_img.size, (255, 255, 255, 255))
            lab_img = Image.composite(white, lab_img, gl)
            mk = Image.new("L", lab_img.size, 0)
            ImageDraw.Draw(mk).rounded_rectangle((0, 0, lab - 1, rowh - 7), 12, fill=255)
            panel.paste(lab_img, (0, y + 3), mk)
            d.line((8, y + 9, lab - 8, y + 9), fill=(255, 255, 255, 140), width=2)
            d.text((lab / 2, y + rowh / 2), tier, font=font(32, 900), fill=(20, 20, 24, 255), anchor="mm")
            if k:
                d.line((lab + 20, y, tw_ - 12, y), fill=(255, 255, 255, 34), width=2)
        slots = {tier: lab + 20 for tier in tiers}
        hold = float(self.cfg.get("hold", 1.3))
        big = None
        for it in items:
            ta = float(it.get("at", self.at + 1))
            if t < ta or it.get("tier") not in tiers:
                continue
            k = tiers.index(it["tier"])
            sw, sh = 210, rowh - 10
            sx, sy = slots[it["tier"]], k * rowh + 5
            slots[it["tier"]] += sw + 10
            rel = t - ta
            land = rel - hold - 0.35
            if 0 <= land < 0.6:     # Aufprall: Reihe leuchtet, Funken fliegen
                fa = 1 - land / 0.6
                fl = Image.new("RGBA", (tw_ - lab - 8, rowh), rgba(TIER_COLORS.get(it["tier"], "#999999"))[:3] + (int(120 * fa),))
                panel.alpha_composite(fl, (lab + 8, k * rowh))
                rng = np.random.default_rng(abs(hash(it["name"])) % 1000)
                for _ in range(16):
                    an, sp = rng.uniform(0, 2 * math.pi), rng.uniform(120, 320)
                    px = sx + sw / 2 + math.cos(an) * sp * land
                    py = sy + sh / 2 + math.sin(an) * sp * land + 400 * land * land
                    r = 5 * fa + 1
                    ImageDraw.Draw(panel).ellipse((px - r, py - r, px + r, py + r), fill=(255, 230, 120, int(255 * fa)))
            if rel < hold:          # groß in der Mitte
                big = (it, rel)
            else:                   # Fallen: von der Mitte in den Slot
                p = ease_in_out(clamp((rel - hold) / 0.35))
                bw, bh = int(tw_ * 0.62), int(th_ * 0.62)
                cx = tw_ / 2 + (sx + sw / 2 - tw_ / 2) * p
                cy = th_ / 2 + (sy + sh / 2 - th_ / 2) * p
                w_ = int(bw + (sw - bw) * p); h_ = int(bh + (sh - bh) * p)
                card_ = item_card(it["name"], max(20, w_), max(14, h_), self.imgs.get(it["name"]), big=p < 0.6)
                panel.alpha_composite(card_, (int(cx - card_.width / 2), int(cy - card_.height / 2)))
        if big:
            it, rel = big
            bw, bh = int(tw_ * 0.62), int(th_ * 0.62)
            s = spring(clamp(rel / 0.7), 6, 1.4)
            card_ = item_card(it["name"], bw, bh, self.imgs.get(it["name"]), big=True)
            paste_scaled(panel, card_, tw_ / 2 + lab / 2, th_ / 2, 0.5 + 0.5 * s, clamp(rel * 6))
        frame = frame.convert("RGBA")
        scale = 0.92 + 0.08 * ease_out_back(clamp(pin))
        cy_ = float(self.cfg.get("y", 0.66)) * H
        if pin * pout > 0.05:  # Milchglas hinter der Tabelle
            gx0, gy0 = W / 2 - tw_ * scale / 2 + (lab + 8) * scale, cy_ - th_ * scale / 2
            g = frame.copy()
            glass(g, (gx0, gy0, W / 2 + tw_ * scale / 2, cy_ + th_ * scale / 2), radius=18, blur=22, tint=(10, 10, 14, 60), border=(255, 255, 255, 0))
            frame = Image.blend(frame, g, clamp(pin * 1.6) * pout)
        paste_scaled(frame, panel, W / 2, cy_, scale, clamp(pin * 1.6) * pout)
        return frame


# =========================================================================== Handy-Orbit (Karussell)

class Orbit(Effect):
    """Karten/Handy-Screens drehen sich als 3D-Karussell vor dem abgedunkelten Video."""

    def covers(self, t):
        return self.at + 0.2 <= t <= self.until

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.6, 0.4)
        if pin <= 0:
            return frame
        if not hasattr(self, "cards"):
            n = int(self.cfg.get("count", 7))
            imgs = load_images(self.cfg, n=n)
            labels = self.cfg.get("labels", [])
            self.cards = [phone_card(imgs[k % len(imgs)] if imgs else None, w=380, h=676, label=labels[k] if k < len(labels) else None, brand=self.brand) for k in range(n)]
        dim = float(self.cfg.get("dim", 0.3)) * clamp(pin * 1.5) * pout
        bg = frame.filter(ImageFilter.GaussianBlur(5 * dim / 0.3)).convert("RGBA")
        bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (0, 0, 0, int(255 * dim))))
        n = len(self.cards)
        R = float(self.cfg.get("radius", 500)) * spring(clamp(pin * 0.9), damping=5.5, freq=1.1)
        sw = float(self.cfg.get("swipe", 0.75))               # alle 0,75 s ein Wisch um eine Karte
        rel = max(0.0, t - self.at - 0.5)
        steps = int(rel / sw) + ease_out_cubic(clamp((rel % sw) / (sw * 0.6)))
        spin = -steps * 2 * math.pi / n
        cy = float(self.cfg.get("y", 0.46)) * H
        placed = []
        for k, c in enumerate(self.cards):
            th = spin + 2 * math.pi * k / n
            x, z = R * math.sin(th), R * math.cos(th)
            persp = 900 / (900 - z * 0.9)
            placed.append((z, x, th, c, persp))
        for z, x, th, c, persp in sorted(placed, key=lambda q: q[0]):
            face = 0.35 + 0.65 * abs(math.cos(th))
            el = c.resize((max(2, int(c.width * face * persp * 0.85)), int(c.height * persp * 0.85)), Image.LANCZOS)
            shade = clamp(0.45 + 0.55 * (z / max(1, R) + 1) / 2)
            if shade < 0.99:
                dark = Image.new("RGBA", el.size, (0, 0, 0, int(255 * (1 - shade))))
                dark.putalpha(Image.fromarray((np.asarray(el.getchannel("A"), dtype=np.float32) * (1 - shade)).astype("uint8")))
                el = Image.alpha_composite(el, dark)
            paste_scaled(bg, el, W / 2 + x, cy - z * 0.16, 1.0, clamp(pin * 2) * pout)
        return bg


# =========================================================================== Punch-in (Zoom-Schnitt)

class Punch(Effect):
    """Harter oder weicher Zoom auf das Gesicht – betont eine Aussage (Jump-Cut-Gefühl)."""

    layer = "pre"

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        z = float(self.cfg.get("zoom", 1.18))
        if self.cfg.get("smooth", False):
            z = 1 + (z - 1) * ease_out_cubic((t - self.at) / 0.35)
        return zoom_frame(frame, z, cx=float(self.cfg.get("cx", 0.5)), cy=float(self.cfg.get("cy", 0.36)))


# =========================================================================== Split-Screen

class MediaReader:
    """Bild oder Video als Quelle; liefert für Zeit t ein passendes Bild (Videos laufen in Echtzeit mit)."""

    def __init__(self, path, size, fy=0.5):
        self.path, self.size, self.fy = path, size, fy
        self.is_img = str(path).lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        self.proc, self.last, self.idx = None, None, -1
        if self.is_img:
            im = Image.open(path).convert("RGB")
            k = max(size[0] / im.width, size[1] / im.height)
            im = im.resize((int(im.width * k) + 1, int(im.height * k) + 1), Image.LANCZOS)
            self.img = im.crop(((im.width - size[0]) // 2, (im.height - size[1]) // 2, (im.width - size[0]) // 2 + size[0], (im.height - size[1]) // 2 + size[1]))

    def get(self, rel_t):
        if self.is_img:
            return self.img
        import subprocess as sp
        from reelkit import FPS, ffmpeg_bin
        w, h = self.size
        if self.proc is None:
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:(iw-{w})/2:(ih-{h})*{self.fy},fps={FPS}"
            self.proc = sp.Popen([ffmpeg_bin(), "-v", "error", "-stream_loop", "-1", "-i", self.path, "-vf", vf,
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=sp.PIPE)
        want = int(rel_t * FPS)
        while self.idx < want:
            buf = self.proc.stdout.read(w * h * 3)
            if len(buf) < w * h * 3:
                break
            self.last = Image.frombuffer("RGB", (w, h), buf, "raw", "RGB", 0, 1).copy()
            self.idx += 1
        return self.last


class Split(Effect):
    """Geteilter Bildschirm: oben Bild/Video/Screenshot, unten die Person (Gesicht im Fokus)."""

    layer = "pre"

    def caption_y(self, t):
        """Untertitel sitzen während des Splits genau auf der Trennlinie."""
        if self.at <= t <= self.until:
            return float(self.cfg.get("ratio", 0.5)) * H

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        ratio = float(self.cfg.get("ratio", 0.5))
        top_h = int(H * ratio)
        if not hasattr(self, "media"):
            if self.cfg.get("grafik"):
                self.media = GraphicSource(self.cfg["grafik"], (W, top_h), self.brand)
            else:
                self.media = MediaReader(self.cfg["media"], (W, top_h), float(self.cfg.get("media_y", 0.5))) if self.cfg.get("media") else None
        out = Image.new("RGB", (W, H), (10, 10, 12))
        p = ease_out_cubic((t - self.at) / 0.3)
        if self.media:
            m = self.media.get(t - self.at)
            if m is not None:
                out.paste(m, (0, int(-top_h * (1 - p))))
        # Person: Ausschnitt um das Gesicht, in die untere Hälfte
        bh = H - top_h
        cy = float(self.cfg.get("face_y", 0.36))
        src_h = int(frame.height * bh / H * float(self.cfg.get("face_zoom", 1.0)) * 1.0)
        src_h = min(frame.height, max(200, src_h))
        y0 = int(clamp(cy * frame.height - src_h * 0.42, 0, frame.height - src_h))
        crop = frame.crop((0, y0, W, y0 + src_h)).resize((W, bh), Image.LANCZOS) if src_h != bh else frame.crop((0, y0, W, y0 + bh))
        out.paste(crop, (0, top_h))
        d = ImageDraw.Draw(out)
        d.line((0, top_h, W, top_h), fill=(255, 255, 255), width=4)
        return out


# =========================================================================== Text hinter dem Kopf

class TextBehind(Effect):
    """Riesiges Wort HINTER der Person (Person freigestellt) – fester Text oder Wort für Wort synchron."""

    _seg = None

    def _word_at(self, t):
        if self.cfg.get("words"):
            if not hasattr(self, "_ws"):
                off = float(self.cfg.get("offset", 0))
                self._ws = [{"w": w["w"].strip(".,!?"), "s": w["s"] - off} for w in load_words(self.cfg["words"])
                            if self.at + off - 0.05 <= w["s"] < self.until + off]
            cur = [w for w in self._ws if w["s"] <= t]
            return (cur[-1]["w"], cur[-1]["s"]) if cur else (None, None)
        return self.cfg.get("text", "KI"), self.at

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.3, 0.3)
        if pin <= 0:
            return frame
        word, ws = self._word_at(t)
        if not word:
            return frame
        if TextBehind._seg is None:
            from segment import Segmenter
            TextBehind._seg = Segmenter(self.cfg.get("quality", "fast"))
        txt = word.upper() if self.cfg.get("gross", True) else word
        size = int(self.cfg.get("size", 0)) or 420
        f = font(size, 900)
        while text_size(txt, f)[0] > W * 0.94 and size > 80:
            size -= 12
            f = font(size, 900)
        col = rgba(self.cfg.get("color", "#FFFFFF"))
        el = text_img(txt, f, fill=col, shadow_alpha=90, pad=40)
        p = ease_out_cubic(clamp((t - ws) / 0.25))
        base = frame.convert("RGBA")
        lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        paste_scaled(lay, el, W / 2, float(self.cfg.get("y", 0.24)) * H, 1.18 - 0.18 * p, clamp(p * 1.5) * pout)
        out = Image.alpha_composite(base, lay)
        out.paste(frame.convert("RGBA"), (0, 0), self._seg.mask(frame, t))
        return out


# =========================================================================== Zoom-Durchschnitt (Übergang)

class ZoomThrough(Effect):
    """Übergang: schneller Zoom IN die Szene bis zum Schnitt, danach Zoom heraus – mit Bewegungsunschärfe."""

    layer = "pre"

    def apply(self, frame, t):
        d = float(self.cfg.get("dauer", 0.5)) / 2
        cut = self.at
        if not (cut - d <= t <= cut + d):
            return frame
        zmax = float(self.cfg.get("zoom", 2.8))
        cx, cy = float(self.cfg.get("cx", 0.5)), float(self.cfg.get("cy", 0.4))
        p = (t - (cut - d)) / d if t < cut else 1 - (t - cut) / d
        p = ease_in_out(clamp(p)) if t < cut else ease_out_cubic(clamp(p))
        z = 1 + (zmax - 1) * p
        out = zoom_frame(frame, z, cx, cy)
        if p > 0.15:   # radiale Bewegungsunschärfe aus mehreren Zoomstufen
            acc = np.asarray(out, dtype=np.float32)
            for k in (1, 2, 3):
                acc += np.asarray(zoom_frame(frame, z * (1 + 0.035 * k * p), cx, cy), dtype=np.float32)
            out = Image.fromarray((acc / 4).astype("uint8"))
        if self.cfg.get("blitz", True) and abs(t - cut) < 0.05:
            out = Image.blend(out, Image.new("RGB", out.size, (255, 255, 255)), 0.5)
        return out


# =========================================================================== Chat-Blasen

class ChatBubbles(Effect):
    """Nachrichten ploppen wie in iMessage/WhatsApp auf (mit Tipp-Animation vor eingehenden Nachrichten)."""

    def occupied(self, t):
        if self.at <= t <= self.until + 0.3:
            y0 = float(self.cfg.get("y", 0.07)) * H
            return (y0, y0 + 130 * len(self.cfg.get("messages", [])))

    def _bubble(self, text, right, w_max=640):
        f = font(46, 700)
        text = clean_text(text, "DMSans-700.ttf")
        words, lines, cur = text.split(), [], ""
        for wd in words:
            if text_size((cur + " " + wd).strip(), f)[0] > w_max - 60:
                lines.append(cur); cur = wd
            else:
                cur = (cur + " " + wd).strip()
        lines.append(cur)
        lh = 60
        bw = max(text_size(l, f)[0] for l in lines) + 60
        bh = lh * len(lines) + 34
        img = Image.new("RGBA", (bw + 20, bh + 20), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        bg = rgba(self.cfg.get("farbe_rechts", self.brand["accent"])) if right else (233, 233, 236, 255)
        fg = (255, 255, 255, 255) if right else (18, 18, 20, 255)
        d.rounded_rectangle((0 if right else 12, 0, bw + (0 if right else 12), bh), 30, fill=bg)
        tail = [(bw - 6, bh - 26), (bw + 14, bh + 2), (bw - 30, bh - 4)] if right else [(18, bh - 26), (-2 + 2, bh + 2), (42, bh - 4)]
        d.polygon(tail, fill=bg)
        for k, l in enumerate(lines):
            d.text((30 + (0 if right else 12), 17 + k * lh), l, font=f, fill=fg)
        return img

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.2, 0.3)
        if pin <= 0:
            return frame
        msgs = self.cfg.get("messages", [])
        frame = frame.convert("RGBA")
        y = float(self.cfg.get("y", 0.07)) * H
        for k, m in enumerate(msgs):
            ta = float(m.get("at", self.at + 0.8 * k))
            right = m.get("von", "links") == "rechts"
            typing = float(m.get("tippen", 0.0 if right else 0.3))
            if t < ta - typing:
                break
            x_edge = W - 50 if right else 50
            if t < ta:  # Tipp-Indikator
                bub = Image.new("RGBA", (150, 84), (0, 0, 0, 0))
                d = ImageDraw.Draw(bub)
                d.rounded_rectangle((0, 0, 149, 83), 40, fill=(233, 233, 236, 255))
                for i in range(3):
                    a = 0.5 + 0.5 * math.sin((t * 8) - i * 0.9)
                    c = int(150 - 60 * a)
                    d.ellipse((30 + i * 34, 30, 52 + i * 34, 52), fill=(c, c, c, 255))
                paste_scaled(frame, bub, x_edge + (-75 if right else 75), y + 42, 1.0, pout)
                break
            bub = self._bubble(m["text"], right)
            s = spring(clamp((t - ta) / 0.4), 7.5, 1.8)
            cx = x_edge - bub.width / 2 if right else x_edge + bub.width / 2
            paste_scaled(frame, bub, cx, y + bub.height / 2 + (1 - clamp(s)) * 30, 0.7 + 0.3 * s, clamp((t - ta) * 8) * pout)
            y += bub.height + 14
        return frame


# =========================================================================== Kommentar-Antwort (Instagram-Sticker)

class CommentReply(Effect):
    """'Antwort auf den Kommentar von …'-Sticker wie bei Instagram – perfekt als Hook."""

    def occupied(self, t):
        if self.at <= t <= self.until + 0.3:
            y = float(self.cfg.get("y", 0.16)) * H
            return (y - 110, y + 110)

    def apply(self, frame, t):
        pin, pout = window(t, self.at, self.until, 0.5, 0.3)
        if pin <= 0:
            return frame
        if not hasattr(self, "img"):
            name = self.cfg.get("name", "lena.marketing")
            text = clean_text(self.cfg.get("text", "Wie hast du das mit Claude gemacht?"))
            f = font(40, 800)
            fh = font(24, 700)
            words, lines, cur = text.split(), [], ""
            for wd in words:
                if text_size((cur + " " + wd).strip(), f)[0] > 700:
                    lines.append(cur); cur = wd
                else:
                    cur = (cur + " " + wd).strip()
            lines.append(cur)
            cw = max(max(text_size(l, f)[0] for l in lines), text_size(f"Antwort auf den Kommentar von {name}", fh)[0] + 70) + 70
            ch = 92 + 52 * len(lines)
            img, pad = card(cw, ch, radius=26, fill=(255, 255, 255, 255))
            d = ImageDraw.Draw(img)
            d.ellipse((pad + 26, pad + 22, pad + 62, pad + 58), fill=rgba(self.brand["accent2"]))
            d.text((pad + 44, pad + 40), name[:1].upper(), font=font(22, 900), fill=(255, 255, 255, 255), anchor="mm")
            d.text((pad + 76, pad + 40), f"Antwort auf den Kommentar von {name}", font=fh, fill=(120, 120, 128, 255), anchor="lm")
            for k, l in enumerate(lines):
                d.text((pad + 30, pad + 78 + k * 52), l, font=f, fill=(16, 16, 18, 255))
            d.polygon([(pad + 40, pad + ch - 2), (pad + 74, pad + ch - 2), (pad + 46, pad + ch + 26)], fill=(255, 255, 255, 255))
            self.img = img
        s = spring(clamp(pin * 0.8), 6.5, 1.5)
        frame = frame.convert("RGBA")
        paste_scaled(frame, self.img, W / 2, float(self.cfg.get("y", 0.16)) * H + (1 - clamp(s)) * 50, 0.75 + 0.25 * s, clamp(pin * 2) * pout)
        return frame


# =========================================================================== Große Worte (Kinetische Typo)

class BigWords(Effect):
    """Vollbild-Typo: jedes gesprochene Wort erscheint riesig, betonte Wörter in Akzentfarbe/Serif."""

    def covers(self, t):
        return self.at <= t <= self.until

    def apply(self, frame, t):
        if not (self.at <= t <= self.until):
            return frame
        if not hasattr(self, "_ws"):
            off = float(self.cfg.get("offset", 0))
            if self.cfg.get("words"):
                self._ws = [{"w": w["w"], "s": w["s"] - off} for w in load_words(self.cfg["words"]) if self.at + off - 0.05 <= w["s"] < self.until + off]
            else:
                toks = self.cfg.get("text", "Jeden Tag ein neuer KI-Trick").split()
                step = (self.until - self.at) / max(1, len(toks))
                self._ws = [{"w": w, "s": self.at + i * step} for i, w in enumerate(toks)]
            self.bet = {w.lower().strip(".,!?") for w in self.cfg.get("betonen", [])}
        cur = [w for w in self._ws if w["s"] <= t] or self._ws[:1]
        w = cur[-1]
        hg = self.cfg.get("hintergrund", "blur")
        if hg == "blur":
            bg = frame.filter(ImageFilter.GaussianBlur(28)).convert("RGBA")
            bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (0, 0, 0, 150)))
        else:
            bg = Image.new("RGBA", (W, H), rgba(self.brand["accent"] if hg == "marke" else "#0B0B0D"))
        key = w["w"].lower().strip(".,!?")
        emph = key in self.bet
        txt = w["w"].strip(",")
        size = 300
        f = font_named("InstrumentSerif-400-italic.ttf", int(size * 1.25)) if emph else font(size, 900)
        while text_size(txt, f)[0] > W * 0.88 and size > 60:
            size -= 10
            f = font_named("InstrumentSerif-400-italic.ttf", int(size * 1.25)) if emph else font(size, 900)
        col = rgba(self.cfg.get("color", self.brand["accent2"])) if emph else (255, 255, 255, 255)
        el = text_img(txt, f, fill=col, shadow_alpha=120, pad=30)
        p = ease_out_back(clamp((t - w["s"]) / 0.18))
        paste_scaled(bg, el, W / 2, H / 2, 1.12 - 0.12 * p, clamp((t - w["s"]) * 10 + 0.3))
        fade = clamp((t - self.at) / 0.1) * clamp((self.until - t) / 0.1)
        return Image.blend(frame.convert("RGBA"), bg, fade) if fade < 1 else bg


# =========================================================================== Registry

REGISTRY = {
    "punch": Punch,
    "split": Split,
    "preis-tag": PriceTag,
    "text-hinter-kopf": TextBehind,
    "zoom-durchschnitt": ZoomThrough,
    "chat-blasen": ChatBubbles,
    "kommentar-antwort": CommentReply,
    "grosse-worte": BigWords,
    "untertitel": Captions,
    "titel": Title,
    "glas-chart": GlassChart,
    "schalter": Toggles,
    "beweis-karte": ProofCard,
    "tiefen-ui": DepthUI,
    "wort-zoom": WordZoom,
    "glitch-push": GlitchPush,
    "pixel-push": PixelPush,
    "tier-liste": TierList,
    "handy-orbit": Orbit,
}


def build(effects_cfg: list[dict], brand: dict) -> list[Effect]:
    out = []
    for c in effects_cfg:
        typ = c.get("type")
        if typ not in REGISTRY:
            raise SystemExit(f"Unbekannter Effekt '{typ}'. Verfügbar: {', '.join(REGISTRY)}")
        out.append(REGISTRY[typ](c, brand))
    return out


def chain(effects: list[Effect]):
    pre = [e for e in effects if e.layer in ("pre", "both")]
    post = [e for e in effects if e.layer in ("post", "both")]
    post.sort(key=lambda e: isinstance(e, Captions))  # Untertitel immer ganz oben

    def run(frame, t, i):
        for e in pre:
            frame = e.zoom(frame, t) if hasattr(e, "zoom") else e.apply(frame, t)
        boxes = [b for b in (e.occupied(t) for e in post if not isinstance(e, Captions)) if b]
        covered = any(e.covers(t) for e in post if not isinstance(e, Captions))
        cap_y = next((y for y in (e.caption_y(t) for e in pre if hasattr(e, "caption_y")) if y), None)
        for e in post:
            if isinstance(e, Captions):
                if covered:
                    continue
                e.avoid = boxes
                e.y_override = cap_y
            frame = e.apply(frame, t)
        return frame

    return run


# Pro-Effekte (Freistellung, Bild-Verwandlungen) nachladen
from effects_pro import PRO  # noqa: E402

REGISTRY.update(PRO)

# Runde 3 (Vogue-Cover, Hollywood-Scan, Instagram-iPhone, Dolly-Zoom, …)
from effects_v3 import V3  # noqa: E402

REGISTRY.update(V3)
REGISTRY["news-matchcut"] = REGISTRY["wort-zoom"]
