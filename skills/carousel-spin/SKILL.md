---
name: carousel-spin
description: POV-Carousel: Handy in der Hand gefilmt – die Reels fliegen aus dem Display auf einen 3D-Ring über dem Handy, spielen ab und werden Karte für Karte weitergewischt. Hand und Handy bleiben scharf davor.
---

# /carousel-spin

Für Videos, in denen jemand das Handy in der Hand hält (POV, über der Schulter). Das Handy wird automatisch erkannt und verfolgt, darüber entsteht ein leuchtender Ring aus Reel-Karten mit @-Handles.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Vorher `python S/setup.py --tiefe`. Als `images` Reel-Videos (oder Bilder) angeben, als `labels` die @-Handles. Dauer = fast das ganze Video. Wird das Handy nicht erkannt (dunkles Display), `handy_x`/`handy_y` (0–1) setzen. `hoehe` = Abstand Ring über dem Handy, `swipe` = Sekunden pro Wisch.

## Plan-Vorlage
```json
{
  "input": "VIDEO",
  "output": "reel-arbeit/reel.mp4",
  "effects": [
    {
      "type": "carousel-spin",
      "at": 0.3,
      "until": 6.0,
      "images": [
        "broll/creator/reel1.mp4",
        "broll/creator/reel2.mp4"
      ],
      "labels": [
        "@creator1",
        "@creator2"
      ]
    }
  ]
}
```

## Worauf achten
Nur Reels verwenden, deren Creator zugestimmt haben, und sie in der Caption taggen. Display hell, Handy hochkant.
