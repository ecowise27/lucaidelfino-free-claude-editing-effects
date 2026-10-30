---
name: news-matchcut
description: Artikel-Schnitt auf ein Wort: Schnelle Schnitte durch mehrere Zeitungsartikel, das markierte Schlüsselwort bleibt immer an derselben Stelle stehen. Nutzen als Pattern-Interrupt, wenn ein Tool, Name oder Kernbegriff fällt.
---

# /news-matchcut

Für 1–2 s wird auf Artikel geschnitten (dunkel, Zeitungspapier, Schreibmaschine …), alle ~0,3 s ein neuer. Das Wort steht in einer roten Box fest in der Bildmitte, der Rest ist unscharf. Ton läuft weiter.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Wähle das wichtigste Wort (Tool-Name, Kernbegriff). `at` = Wortbeginn − 0,1 s, `until` = `at` + 1,3–1,8 s. Optional `text` = 3–4 Sätze zum Thema, damit der Artikeltext passt (sonst neutraler Standardtext). Farbe der Box per `color` (Standard Rot wie im Original, Lucas Lila: `#5A3DF5`).

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
      "type": "news-matchcut",
      "at": 4.0,
      "until": 5.6,
      "word": "Claude"
    }
  ]
}
```

## Worauf achten
Höchstens einmal pro 10 Sekunden. Untertitel blenden sich währenddessen automatisch aus.
