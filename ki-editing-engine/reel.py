"""Ein Video mit einem oder mehreren Effekten rendern.

Variante A – ein Effekt direkt:
  python reel.py -i clip.mp4 -o out.mp4 --effect schalter --set at=2.1 --set items='["Ein Prompt","Einfügen","Fertig"]'

Variante B – Plan-Datei mit mehreren Effekten (empfohlen):
  python reel.py --plan plan.json

plan.json:
{
  "input": "clip.mp4", "output": "reel.mp4", "start": 0, "end": 18.5,
  "effects": [
    {"type": "untertitel", "words": "words.json", "style": "brust"},
    {"type": "glas-chart", "at": 3.2, "until": 6.5, "label": "Reichweite", "value": 67, "suffix": "%"}
  ]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from effects import REGISTRY, build, chain  # noqa: E402
from reelkit import Job, load_brand, render  # noqa: E402


def parse_val(v: str):
    try:
        return json.loads(v)
    except json.JSONDecodeError:
        return v


def main():
    ap = argparse.ArgumentParser(description="Reel-Effekte rendern")
    ap.add_argument("--plan", help="plan.json mit input/output/effects")
    ap.add_argument("--input", "-i")
    ap.add_argument("--output", "-o")
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--effect", help=f"Einzelner Effekt: {', '.join(REGISTRY)}")
    ap.add_argument("--set", action="append", default=[], help="key=value für den Effekt (Wert darf JSON sein)")
    ap.add_argument("--brand", help="brand.json mit eigenen Farben")
    ap.add_argument("--preview", type=float, help="Nur ein Standbild bei Sekunde X als PNG speichern")
    a = ap.parse_args()

    plan = json.loads(Path(a.plan).read_text()) if a.plan else {"effects": []}
    for k in ("input", "output", "start", "end"):
        if getattr(a, k) is not None:
            plan[k] = getattr(a, k)
    if a.effect:
        cfg = {"type": a.effect}
        for kv in a.set:
            k, _, v = kv.partition("=")
            cfg[k] = parse_val(v)
        plan["effects"].append(cfg)
    if not plan.get("input") or not plan.get("output"):
        sys.exit("input und output fehlen")

    brand = load_brand(a.brand or plan.get("brand"))
    start = float(plan.get("start", 0))
    for e in plan["effects"]:  # Untertitel brauchen den Versatz zum Original
        e.setdefault("_input", plan["input"])
        e.setdefault("_start", start)
        if e.get("type") == "untertitel" or "words" in e:
            e.setdefault("offset", start)
    effects = build(plan["effects"], brand)
    run = chain(effects)

    if a.preview is not None:
        from preview import still
        still(plan["input"], start + a.preview, a.preview, run, plan["output"])
        return
    render(Job(plan["input"], plan["output"], start, plan.get("end")), run)


if __name__ == "__main__":
    main()
