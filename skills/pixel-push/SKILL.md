---
name: pixel-push
description: Pixel-Laufschrift: Die gesprochenen Wörter erscheinen nacheinander als riesige, gut lesbare LED-Pixelschrift und werden mit Bewegungsunschärfe weitergeschoben. Für Kernaussagen und Twists.
---

# /pixel-push

Schnitt auf einen schwarzen LED-Screen: jedes Wort steht groß in der Mitte, beim nächsten Wort schiebt es sich blitzschnell zur Seite.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Einen starken Satz (3–8 Wörter) wählen, `at`/`until` auf Anfang/Ende, `words` = words.json. Ohne Transkript `text`.

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
      "type": "pixel-push",
      "at": 6.0,
      "until": 8.6,
      "words": "reel-arbeit/words.json"
    }
  ]
}
```

## Worauf achten
Die Schriftgröße passt sich automatisch an das längste Wort an.
