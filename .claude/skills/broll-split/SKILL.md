---
name: broll-split
description: B-Roll-Split: Oben läuft ein B-Roll-Video (z. B. Parfüm-Werbung, Produkt, Ort), unten die Person, Untertitel auf der Trennlinie – dazu ein Preisschild, das hochzählt.
---

# /broll-split

Der Bildschirm teilt sich: oben das bewegte B-Roll, unten die Person. Auf dem B-Roll landet ein Preisschild, dessen Zahl bei jeder Nennung hochspringt.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
B-Roll als **Video** (`media`, bevorzugt) oder Bild. Zahlen aus dem Gesagten als `values`/`times`. `untertitel` dazunehmen.

## Plan-Vorlage
```json
{
  "input": "VIDEO",
  "output": "reel-arbeit/reel.mp4",
  "effects": [
    {
      "type": "split",
      "at": 1.0,
      "until": 5.0,
      "media": "broll/produkt.mp4"
    },
    {
      "type": "preis-tag",
      "at": 1.2,
      "until": 5.0,
      "values": [
        29,
        99,
        199
      ],
      "times": [
        1.4,
        2.4,
        3.4
      ]
    },
    {
      "type": "untertitel",
      "words": "reel-arbeit/words.json",
      "style": "akzent"
    }
  ]
}
```

## Worauf achten
Nur B-Roll verwenden, an dem ihr die Rechte habt (eigene Aufnahmen, KI-generiert oder lizenziert).
