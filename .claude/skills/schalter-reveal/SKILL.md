---
name: schalter-reveal
description: Einstellungs-Karte im Apple-Stil, deren Schalter einer nach dem anderen auf AN springen. Nutzen für Aufzählungen, Schritte oder Checklisten im Video ("Erstens … zweitens …").
---

# /schalter-reveal

Eine weiße iOS-Karte mit 3–4 Zeilen erscheint; bei jedem genannten Punkt springt der passende Schalter grün an.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Finde im Transkript die 3–4 Punkte der Aufzählung. `items` = je 2–4 Wörter. `times` = Startzeit jedes Punktes (Wort, mit dem der Punkt beginnt).

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
      "type": "schalter",
      "at": 2.0,
      "items": [
        "Ein Prompt",
        "In Claude einfügen",
        "Fertiges Ergebnis"
      ],
      "times": [
        2.4,
        3.3,
        4.2
      ]
    }
  ]
}
```

## Worauf achten
Mehr als 4 Zeilen werden unruhig – lieber zusammenfassen.
