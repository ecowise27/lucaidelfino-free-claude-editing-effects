---
name: koerper-orbit
description: Reels kreisen um den Körper: Reel-Karten (Videos anderer Creator oder eigene) drehen sich auf einem 3D-Ring um die Person – vorne vor ihr, hinten hinter ihr (Freistellung). Mit @-Handles, ideal als Hook.
---

# /koerper-orbit

Die Person steht im Zentrum, ein Ring aus laufenden Reels dreht sich um ihren Oberkörper.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Vorher `python S/setup.py --tiefe`. `images` = Reel-Videos, `labels` = @-Handles. `y` = Höhe des Rings (0,5–0,65), `radius`, `speed` (Umdrehungen/Sek.). Dazu meist `titel` mit `box: weiss`.

## Plan-Vorlage
```json
{
  "input": "VIDEO",
  "output": "reel-arbeit/reel.mp4",
  "effects": [
    {
      "type": "titel",
      "at": 0,
      "until": 3,
      "text": "Claude schneidet|jetzt meine Reels",
      "box": "weiss"
    },
    {
      "type": "koerper-orbit",
      "at": 0,
      "until": 3.2,
      "images": [
        "broll/creator/reel1.mp4"
      ],
      "labels": [
        "@creator"
      ]
    }
  ]
}
```

## Worauf achten
Nur Reels mit Zustimmung der Creator, in der Caption taggen.
