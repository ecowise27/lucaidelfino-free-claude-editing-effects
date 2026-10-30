---
name: business-reel
description: Business-Reel-Look: Hook-Titel oben (weiß, zweite Zeile in Box), dahinter und davor fächern sich Reels von Creatorn auf (mit @-Handle), die Person steht in der Mitte, Untertitel mittig.
---

# /business-reel

Wie bei den großen Business-Creatorn: Die Person wird freigestellt, rundherum fliegen Reel-Karten anderer Creator/eigene Reels in einem Fächer ein – manche hinter, manche vor der Person.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Vorher `python S/setup.py --tiefe` (Freistellung der Person). `tiefen-ui` mit `style: faecher`, `images`/Videos der Reels und `labels` mit @-Handles; dazu `titel` mit `box: weiss`. Nur Reels verwenden, deren Creator zugestimmt haben (oder eigene).

## Plan-Vorlage
```json
{
  "input": "VIDEO",
  "output": "reel-arbeit/reel.mp4",
  "effects": [
    {
      "type": "titel",
      "at": 0,
      "until": 4,
      "text": "Mach deine Videos|zu gut zum Skippen",
      "box": "weiss"
    },
    {
      "type": "tiefen-ui",
      "at": 0.3,
      "until": 4,
      "style": "faecher",
      "images": [
        "broll/creator/mariah.mp4"
      ],
      "labels": [
        "@learnaiwithmariah"
      ],
      "y": 0.42
    },
    {
      "type": "untertitel",
      "words": "reel-arbeit/words.json",
      "style": "brust",
      "y": 0.52
    }
  ]
}
```

## Worauf achten
Creator in der Caption taggen.
