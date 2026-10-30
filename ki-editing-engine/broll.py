"""B-Roll-Archiv: eigene Clips einmal erfassen, danach in normaler Sprache durchsuchen.

1) Erfassen – macht pro Clip ein Vorschaubild-Raster und trägt ihn in die Bibliothek ein:
     python broll.py erfassen --ordner broll/
   → broll/_archiv/<clip>.jpg (4 Standbilder)  und  broll/_archiv/bibliothek.json
   Danach schaut Claude sich die Raster an und füllt für jeden Clip "beschreibung" und "tags"
   in bibliothek.json aus (z. B. "Saugroboter fährt über Holzboden, warmes Licht").

2) Suchen:
     python broll.py suchen --ordner broll/ "saugroboter wohnzimmer"
   → beste Treffer mit Pfad, Dauer und Beschreibung.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image, ImageDraw  # noqa: E402

from reelkit import probe  # noqa: E402

VIDEO = (".mp4", ".mov", ".m4v", ".webm")


def sheet(path: Path, out: Path, n=4):
    from preview import grab
    dur = probe(str(path))["duration"] or 1
    frames = [grab(str(path), dur * (k + 0.5) / n).resize((270, 480)) for k in range(n)]
    s = Image.new("RGB", (n * 276, 500), (20, 20, 20))
    d = ImageDraw.Draw(s)
    for k, f in enumerate(frames):
        s.paste(f, (k * 276, 20))
        d.text((k * 276 + 6, 3), f"{dur * (k + 0.5) / n:.1f}s", fill=(255, 220, 0))
    s.save(out, quality=82)
    return dur


def erfassen(ordner: Path):
    arch = ordner / "_archiv"
    arch.mkdir(exist_ok=True)
    lib_p = arch / "bibliothek.json"
    lib = json.loads(lib_p.read_text()) if lib_p.exists() else {}
    neu = 0
    for p in sorted(ordner.rglob("*")):
        if p.suffix.lower() not in VIDEO or "_archiv" in p.parts:
            continue
        key = str(p.relative_to(ordner))
        if key in lib:
            continue
        img = arch / (re.sub(r"[^\w.-]", "_", key) + ".jpg")
        dur = sheet(p, img)
        lib[key] = {"pfad": str(p), "dauer": round(dur, 1), "vorschau": str(img), "beschreibung": "", "tags": []}
        neu += 1
        print(f"+ {key} ({dur:.1f}s) → {img}")
    lib_p.write_text(json.dumps(lib, ensure_ascii=False, indent=1))
    offen = [k for k, v in lib.items() if not v["beschreibung"]]
    print(f"\n{neu} neu, {len(lib)} gesamt. Ohne Beschreibung: {len(offen)} → Vorschaubilder ansehen und in {lib_p} eintragen.")


def suchen(ordner: Path, frage: str, top=5):
    lib = json.loads((ordner / "_archiv" / "bibliothek.json").read_text())
    q = [w for w in re.findall(r"\w+", frage.lower()) if len(w) > 2]
    scored = []
    for k, v in lib.items():
        text = (v["beschreibung"] + " " + " ".join(v["tags"]) + " " + k).lower()
        score = sum(2 if re.search(rf"\b{re.escape(w)}", text) else (1 if w[:5] in text else 0) for w in q)
        if score:
            scored.append((score, k, v))
    for score, k, v in sorted(scored, key=lambda x: -x[0])[:top]:
        print(f"[{score}] {v['pfad']}  ({v['dauer']}s)  – {v['beschreibung']}")
    if not scored:
        print("Keine Treffer. Tipp: Beschreibungen in bibliothek.json ergänzen oder andere Begriffe probieren.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("erfassen")
    a1.add_argument("--ordner", required=True)
    a2 = sub.add_parser("suchen")
    a2.add_argument("--ordner", required=True)
    a2.add_argument("frage")
    a = ap.parse_args()
    if a.cmd == "erfassen":
        erfassen(Path(a.ordner))
    else:
        suchen(Path(a.ordner), a.frage)


if __name__ == "__main__":
    main()
