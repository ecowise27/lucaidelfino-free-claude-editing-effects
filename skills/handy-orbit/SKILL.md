---
name: handy-orbit
description: Deine Reels auf einem 3D-Ring, Karte für Karte weitergewischt – vor dem leicht abgedunkelten Video. Nutzen, wenn über mehrere Videos, Beispiele, Kunden oder Ergebnisse gesprochen wird ("meine letzten Reels", "20 Templates").
---

# /handy-orbit

Mehrere Reel-Screens fliegen aus der Mitte auf einen Ring und werden alle ~0,75 s um eine Karte weitergewischt; das Video bleibt dahinter sichtbar.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Wenn der Nutzer Bilder/Screenshots mitliefert, als `images` nutzen; sonst werden Standbilder aus dem Clip genommen. `labels` optional ("Tag 1" …). Dauer 2,5–4 s.

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
      "type": "handy-orbit",
      "at": 2.0,
      "until": 5.5,
      "labels": [
        "Reel 1",
        "Reel 2",
        "Reel 3",
        "Reel 4",
        "Reel 5",
        "Reel 6",
        "Reel 7"
      ]
    }
  ]
}
```

## Worauf achten
Mit echten Screenshots (z. B. Instagram-Profil, Ergebnisse) wirkt es am stärksten.
