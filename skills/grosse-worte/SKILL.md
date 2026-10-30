---
name: grosse-worte
description: Kinetische Typo: Die Wörter knallen nacheinander groß ins Bild und bauen sich zu einem Satzblock auf, Schlüsselwörter landen in einer schrägen Lila-Box, mit Kamera-Wackler beim Aufprall.
---

# /grosse-worte

Für 2–4 s wird das Video dunkel-unscharf, der Satz baut sich Wort für Wort in großer Typo auf.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Starken Satz (4–9 Wörter) wählen, `words` = words.json, 1–2 Schlüsselwörter in `betonen`. `hintergrund`: `blur`, `schwarz` oder `marke`.

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
      "type": "grosse-worte",
      "at": 6.0,
      "until": 9.0,
      "words": "reel-arbeit/words.json",
      "betonen": [
        "einfach"
      ]
    }
  ]
}
```

## Worauf achten
Gut direkt nach `zoom-durchschnitt`.
