---
name: chat-blasen
description: Chat-Nachrichten ploppen wie in iMessage/WhatsApp auf – mit Tipp-Animation vor eingehenden Nachrichten. Nutzen für Kundenanfragen, Dialoge ('Chef fragt … ich antworte …') oder Testimonials.
---

# /chat-blasen

Graue Blasen (links, eingehend) und Blasen in Lucas Lila (rechts, ausgehend) erscheinen nacheinander oben im Bild; vor eingehenden Nachrichten tippt es kurz (0,3 s). Der ganze Dialog dauert typischerweise nur 2–3 s.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Formuliere einen kurzen Dialog (2–3 Nachrichten, je max. 6 Wörter), Abstand zwischen den Nachrichten 0,6–0,8 s, `until` direkt nach der letzten Nachricht + 1 s. `at` jeder Nachricht auf den passenden Moment legen. `von`: `links` (andere Person) oder `rechts` (Luca). Keine Emojis.

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
      "type": "chat-blasen",
      "at": 2.0,
      "until": 6.0,
      "messages": [
        {
          "text": "Kannst du das Video bis heute schneiden?",
          "von": "links",
          "at": 2.6
        },
        {
          "text": "Schon fertig. Mit Claude.",
          "von": "rechts",
          "at": 4.2
        }
      ]
    }
  ]
}
```

## Worauf achten
Blasen sitzen oben (y 0,07) – Untertitel weichen automatisch aus. Bei Personen mit hohem Kopf im Bild `y` auf 0,04 senken.
