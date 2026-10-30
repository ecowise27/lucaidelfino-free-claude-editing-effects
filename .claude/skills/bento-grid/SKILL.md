---
name: bento-grid
description: Bento-Grid: Das Video zieht sich in eine Kachel zurück, drumherum bauen sich Bento-Kacheln auf – große Kennzahl, Kurve, echte Tool-Logos, Headline. Apple-Keynote-Look.
---

# /bento-grid

Zoom-out ins Raster: Video links groß, rechts zählt eine Zahl hoch, eine Kurve klettert, unten erscheinen die Logos der Tools, ganz unten eine Headline.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
`titel`, `untertitel`, `zahl`, `zahl_label`, `zahl_suffix`, `logos` (z. B. claude, higgsfield, elevenlabs, notion, canva, gmail, chatgpt, n8n, zapier), `text`, `text2`. Dauer 3–5 s.

## Plan-Vorlage
```json
{
  "input": "VIDEO",
  "output": "reel-arbeit/reel.mp4",
  "effects": [
    {
      "type": "bento-grid",
      "at": 1.0,
      "until": 5.0,
      "titel": "Mein KI-Stack",
      "zahl": 10,
      "zahl_label": "Stunden gespart / Woche",
      "logos": [
        "claude",
        "higgsfield",
        "elevenlabs",
        "notion",
        "canva"
      ]
    }
  ]
}
```

## Worauf achten
Ideal für 'Mein Setup', 'Meine Tools', Ergebnisse.
