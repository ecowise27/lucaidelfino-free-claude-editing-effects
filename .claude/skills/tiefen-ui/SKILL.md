---
name: tiefen-ui
description: Website hinter dem Kopf: Ein Browserfenster mit einer scrollenden Website (Bildschirmaufnahme) schwebt HINTER der Person, Kopf und Hände bleiben davor (Freistellung). Ideal für Shop-, Marken- und Website-Themen.
---

# /tiefen-ui

Ein macOS-Browserfenster mit URL-Leiste erscheint hinter dem Kopf; darin läuft die Bildschirmaufnahme einer Website, die nach unten scrollt.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Vorher `python S/setup.py --tiefe`. Der Nutzer liefert eine Bildschirmaufnahme der Website (einfach durch die Seite scrollen). `style: website`, `media` = Aufnahme, `url` = Adresse in der Leiste, `y` so, dass das Fenster auf Kopfhöhe liegt (Stirn verdeckt die Unterkante), `w` = Breite (1000), `tempo` = Abspielgeschwindigkeit. Alternativ `style: panel` (App-Fenster) oder `faecher` (Reel-Karten).

## Plan-Vorlage
```json
{
  "input": "VIDEO",
  "output": "reel-arbeit/reel.mp4",
  "effects": [
    {
      "type": "tiefen-ui",
      "at": 0,
      "until": 3.5,
      "style": "website",
      "media": "broll/website_scroll.mp4",
      "url": "deine-seite.de",
      "y": 0.27
    }
  ]
}
```

## Worauf achten
Nur Websites zeigen, für die ihr die Erlaubnis habt. Aufnahme vorher auf 10–15 s kürzen und ggf. beschleunigen.
