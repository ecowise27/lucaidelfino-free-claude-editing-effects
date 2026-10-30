---
name: glas-chart
description: Milchglas-Karte mit Kurve, die nach oben klettert, und hochzählender Zahl über dem Video. Nutzen, wenn im Video eine Zahl, ein Wachstum oder ein Ergebnis genannt wird (Umsatz, Reichweite, Prozent).
---

# /glas-chart

Eine durchscheinende Glas-Karte gleitet ins Bild, die Kurve zeichnet sich nach oben, die Zahl zählt bis zum Zielwert hoch.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Suche im Transkript die Stelle, an der die Zahl/das Wachstum genannt wird. Setze `at` ca. 0,3 s vorher, `until` 2,5–4 s später. `value` = die genannte Zahl, `label` = 1–2 Wörter ("Reichweite", "Umsatz").

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
      "type": "glas-chart",
      "at": 3.1,
      "until": 6.4,
      "label": "Reichweite",
      "value": 67,
      "suffix": "%"
    }
  ]
}
```

## Worauf achten
Bei Euro: `"suffix": " €"`. Bei Rückgang eigene `points` absteigend setzen und `color` rot (`#E5484D`).
