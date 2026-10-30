---
name: freeze-sticker
description: Freeze-Sticker: Standbild im Zeitungsdruck-Look (Halbton), die Person wird zum glänzenden Sticker mit dickem Rand, Marker-Beschriftung mit gezeichnetem Pfeil, Kritzel-Sterne und roter Stempel.
---

# /freeze-sticker

Blitz, Standbild, Hintergrund wird Druckraster, die Person hebt sich als Sticker ab (mit Glanzstreifen), Pfeil und Text werden live gezeichnet, ein Stempel knallt drauf.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Vorher `python S/setup.py --tiefe` (Freistellung der Person). `label` (max. 4 Wörter), `seite`, `stempel` (z. B. VORHER, NACHHER, FAIL, LEGENDE), `color` (Marker). Dauer 2–3 s.

## Plan-Vorlage
```json
{
  "input": "VIDEO",
  "output": "reel-arbeit/reel.mp4",
  "effects": [
    {
      "type": "untertitel",
      "words": "reel-arbeit/words.json",
      "style": "brust"
    },
    {
      "type": "freeze-sticker",
      "at": 2.0,
      "until": 4.6,
      "label": "Ich vor Claude",
      "stempel": "VORHER"
    }
  ]
}
```

## Worauf achten
Untertitel blenden sich währenddessen aus.
