---
name: tier-ranking
description: Tier-Listen-Reel: Eine S-bis-F-Tabelle erscheint, jedes genannte Element taucht als große Karte auf und fällt dann in seine Reihe. Dazu ein orangefarbener Ranking-Titel oben. Nutzen für 'Die besten Tools/Plattformen gerankt'.
---

# /tier-ranking

Oben ein kursiver Titel in Großbuchstaben, unten die farbige S–F-Tabelle. Bei jeder Nennung springt eine große Karte (Name + optional Logo) in die Mitte und fällt nach ~1,3 s in ihre Reihe.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Finde im Transkript jedes Element und seine Bewertung. Je Element `{name, tier, at}` (`at` = Zeitpunkt der Nennung), optional `bild` = Logo-Datei. Titel als `titel` mit `box: ranking`. Liste bleibt über die ganze Ranking-Passage stehen; Untertitel weichen automatisch nach oben aus.

## Plan-Vorlage
```json
{
  "input": "VIDEO",
  "output": "reel-arbeit/reel.mp4",
  "effects": [
    {
      "type": "titel",
      "at": 0,
      "until": 14,
      "text": "Die besten KI-Tools|für Einsteiger",
      "box": "ranking"
    },
    {
      "type": "untertitel",
      "words": "reel-arbeit/words.json",
      "style": "brust"
    },
    {
      "type": "tier-liste",
      "at": 1.0,
      "until": 14.0,
      "items": [
        {
          "name": "ChatGPT",
          "tier": "A",
          "at": 2.1
        },
        {
          "name": "Claude",
          "tier": "S",
          "at": 5.4
        },
        {
          "name": "Gemini",
          "tier": "B",
          "at": 9.0
        }
      ]
    }
  ]
}
```

## Worauf achten
Zwischen zwei Nennungen mindestens 1,5 s Abstand, sonst überlagern sich die großen Karten.
