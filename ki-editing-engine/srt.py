"""Untertitel-Datei (.srt) aus words.json – z. B. für YouTube oder Schnittprogramme.

  python srt.py --words words.json --out untertitel.srt [--max-zeichen 42]
"""
import argparse
import json
from pathlib import Path


def ts(x):
    h, r = divmod(x, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-zeichen", type=int, default=42)
    a = ap.parse_args()
    words = json.loads(Path(a.words).read_text())
    blocks, cur = [], []
    for w in words:
        if cur and (len(" ".join(x["w"] for x in cur + [w])) > a.max_zeichen or w["s"] - cur[-1]["e"] > 0.8):
            blocks.append(cur)
            cur = []
        cur.append(w)
        if w["w"].endswith((".", "!", "?")):
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    out = []
    for k, b in enumerate(blocks, 1):
        out.append(f"{k}\n{ts(b[0]['s'])} --> {ts(b[-1]['e'])}\n{' '.join(x['w'] for x in b)}\n")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(out))
    print(f"{len(blocks)} Untertitel → {a.out}")


if __name__ == "__main__":
    main()
