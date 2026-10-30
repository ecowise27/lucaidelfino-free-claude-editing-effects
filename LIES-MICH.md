# KI-Editing-Pack · 16 Effekte für Claude Code

👉 Ausführliche Schritt-für-Schritt-Anleitung mit Bildern: **ANLEITUNG - zuerst lesen.pdf**

Video anhängen, `/befehl` tippen – Claude schneidet dein Reel und baut den Effekt ein.

## Installation

**Variante 1 – Doppelklick (am einfachsten)**
- Mac: `install-mac.command` doppelklicken (beim ersten Mal: Rechtsklick → Öffnen).
- Windows: Rechtsklick auf `install-windows.ps1` → „Mit PowerShell ausführen“.
- Danach Claude Code neu starten und `/` tippen – die Effekte erscheinen in der Liste.

**Variante 2 – Als Plugin über GitHub**
```
/plugin marketplace add ecowise27/lucaidelfino-free-claude-editing-effects
/plugin install lucaidelfino-free-claude-editing-effects@ecowise27
```
Befehle heißen dann `/lucaidelfino-free-claude-editing-effects:glas-chart` – meist reicht einfach `/glas-chart`. Updates: `/plugin marketplace update ecowise27`.

**Variante 4 – Am Handy (Code-Tab)**
Auf github.com/ecowise27/lucaidelfino-free-claude-editing-effects „Use this template“ → eigenes Repository erstellen → in der Claude-App im Code-Tab auswählen. Die Skills liegen dafür im Ordner `.claude/skills`.

**Variante 3 – Nur für ein Projekt**
Den Ordner `skills` in dein Projekt nach `.claude/skills` kopieren.

## Voraussetzungen
- Claude Code (Terminal, Desktop-App oder VS Code)
- Python 3.10+ – fehlende Pakete (Pillow, numpy, MediaPipe, faster-whisper) und ffmpeg installiert der erste Befehl automatisch.
- Beim ersten Mal lädt die Untertitel-Erkennung ein Sprachmodell (~460 MB).

## Die Befehle
| Befehl |
|---|
| `/bento-grid` |
| `/beweis-karte` |
| `/broll-split` |
| `/business-reel` |
| `/carousel-spin` |
| `/chat-blasen` |
| `/freeze-sticker` |
| `/glas-chart` |
| `/grosse-worte` |
| `/handy-orbit` |
| `/koerper-orbit` |
| `/news-matchcut` |
| `/pixel-push` |
| `/schalter-reveal` |
| `/tiefen-ui` |
| `/tier-ranking` |

## Tipps
- Am besten Hochformat-Videos, Kopf und Oberkörper im Bild, ruhiger Hintergrund.
- Eigene Farben: `brand.json` in den Projektordner legen, z. B. `{"accent": "#FF5A00", "highlight": "#FF5A00"}`.
- Fremde Videos, Logos und Websites nur mit Erlaubnis verwenden.

Erstellt von @lucaidelfino
