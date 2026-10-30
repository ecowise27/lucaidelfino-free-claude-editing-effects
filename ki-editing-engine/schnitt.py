"""Schnitt-Werkzeug: Pausen rausschneiden, Abschnitte auswählen, als 9:16 oder 16:9 zusammensetzen.

Pausen automatisch entfernen (braucht words.json aus transcribe.py):
  python schnitt.py -i roh.mp4 -o geschnitten.mp4 --words words.json --auto-pausen [--max-pause 0.35]

Nur bestimmte Abschnitte behalten (z. B. die besten Stellen eines langen Videos):
  python schnitt.py -i lang.mp4 -o clip1.mp4 --keep 12.4-31.0 --keep 45.2-58.9

Format: --format 9x16 (Reel, Standard) | 16x9 (YouTube) | original
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reelkit import ffmpeg_bin, probe  # noqa: E402


def ranges_from_words(words, max_pause=0.35, pad=0.08, total=None):
    """Behalte Bereiche, in denen gesprochen wird; Pausen > max_pause fliegen raus."""
    if not words:
        return [(0.0, total or 0.0)]
    out = []
    s, e = max(0.0, words[0]["s"] - pad), words[0]["e"] + pad
    for w in words[1:]:
        if w["s"] - e > max_pause:
            out.append((s, e))
            s = max(0.0, w["s"] - pad)
        e = w["e"] + pad
    out.append((s, min(e, total) if total else e))
    return out


def remap_words(words, ranges):
    """Wort-Zeitstempel auf die geschnittene Zeitachse umrechnen."""
    out, acc = [], 0.0
    for a, b in ranges:
        for w in words:
            if a <= w["s"] < b:
                out.append({"w": w["w"], "s": round(w["s"] - a + acc, 3), "e": round(min(w["e"], b) - a + acc, 3)})
        acc += b - a
    return out


def cut(inp, out, ranges, fmt="9x16"):
    ff = ffmpeg_bin()
    has_audio = probe(inp)["has_audio"]
    if fmt == "9x16":
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30"
    elif fmt == "16x9":
        vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30"
    else:
        vf = "setsar=1,fps=30"
    parts = []
    for k, (a, b) in enumerate(ranges):
        parts.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,{vf}[v{k}]")
        if has_audio:
            parts.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={max(0, b - a - 0.03):.3f}:d=0.03[a{k}]")
    n = len(ranges)
    if has_audio:
        parts.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
        maps = ["-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    else:
        parts.append("".join(f"[v{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0[v]")
        maps = ["-map", "[v]"]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(";\n".join(parts))
        script = fh.name
    subprocess.run([ff, "-v", "error", "-y", "-i", inp, "-filter_complex_script", script, *maps,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True)
    ap.add_argument("--output", "-o", required=True)
    ap.add_argument("--words", help="words.json (für --auto-pausen und neue Zeitstempel)")
    ap.add_argument("--auto-pausen", action="store_true", help="Sprechpausen automatisch entfernen")
    ap.add_argument("--max-pause", type=float, default=0.35)
    ap.add_argument("--keep", action="append", default=[], help="Bereich behalten, z. B. 12.4-31.0 (mehrfach möglich)")
    ap.add_argument("--format", default="9x16", choices=["9x16", "16x9", "original"])
    ap.add_argument("--fuellwoerter", action="store_true", help="äh, ähm, öhm … zusätzlich rausschneiden")
    a = ap.parse_args()

    total = probe(a.input)["duration"]
    words = json.loads(Path(a.words).read_text()) if a.words else []
    if a.fuellwoerter:
        filler = {"äh", "ähm", "öh", "öhm", "hm", "hmm", "ehm", "em", "uh", "um"}
        words = [w for w in words if w["w"].lower().strip(".,!?") not in filler]
    if a.keep:
        ranges = [tuple(float(x) for x in k.split("-")) for k in a.keep]
        if a.auto_pausen and words:  # innerhalb der Abschnitte zusätzlich Pausen kürzen
            ranges = [r for (s, e) in ranges for r in ranges_from_words([w for w in words if s <= w["s"] < e], a.max_pause, total=e)]
    elif a.auto_pausen:
        if not words:
            sys.exit("--auto-pausen braucht --words words.json")
        ranges = ranges_from_words(words, a.max_pause, total=total)
    else:
        ranges = [(0.0, total)]
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    cut(a.input, a.output, ranges, a.format)
    kept = sum(b - x for x, b in ranges)
    print(f"{len(ranges)} Abschnitte, {kept:.1f}s von {total:.1f}s behalten → {a.output}")
    if words:
        nw = remap_words(words, ranges)
        wp = Path(a.output).with_suffix(".words.json")
        wp.write_text(json.dumps(nw, ensure_ascii=False))
        print(f"Neue Wort-Zeitstempel → {wp}")


if __name__ == "__main__":
    main()
