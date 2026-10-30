# Ablauf für jeden Reel-Skill

Alle Skripte liegen im Ordner `ki-editing-engine` (im Folgenden `S`).
Arbeite in einem eigenen Arbeitsordner (z. B. `./reel-arbeit/`), damit nichts überschrieben wird.

## 1. Video finden
- Hat der Nutzer ein Video angehängt, nimm diese Datei. Sonst im Projekt nach der neuesten `.mp4` / `.mov` suchen.
- Findest du keins: kurz nach dem Video fragen und stoppen.
- iPhone-Videos (`.MOV`, Hochformat) gehen direkt – Drehung wird automatisch erkannt.

## 2. Vorbereiten (einmal pro Sitzung)
```bash
python S/setup.py --tiefe    # --tiefe installiert die Freistellung (für fast alle Effekte nötig)
```

## 3. Transkribieren
```bash
python S/transcribe.py -i VIDEO -o reel-arbeit/words.json
```
Lies danach `reel-arbeit/words.txt`. Daraus wählst du **wann** ein Effekt kommt
(immer auf das Wort, um das es geht – z. B. die Zahl, das Ergebnis, die Pointe).
Sprache ist Deutsch (`--lang de`); für Englisch `--lang en`.

## 4. Plan schreiben
Lege `reel-arbeit/plan.json` an (Format siehe `EFFEKTE.md`). Regeln:
- Effekte 0,1–0,2 s **vor** dem Schlüsselwort starten, damit sie mit dem Wort landen.
- Texte auf Karten kurz halten (max. 3–4 Wörter pro Zeile), auf Deutsch, in Lucas Ton: einfach, direkt.
- Nicht zwei große Effekte gleichzeitig. Zwischen Effekten 1–2 s nur Untertitel.
- Untertitel (`untertitel`) fast immer dazunehmen – sie weichen Karten automatisch aus.

## 5. Vorschau prüfen (Pflicht)
Für jeden Effekt ein Standbild in der Mitte seines Zeitfensters:
```bash
python S/reel.py --plan reel-arbeit/plan.json --output reel-arbeit/vorschau_3.2.png --preview 3.2
```
Schau dir die PNGs an. Prüfe: verdeckt etwas das Gesicht? Text lesbar? Nichts abgeschnitten?
Wenn nötig `y`, `x`, `side`, Texte oder Zeiten anpassen und erneut prüfen.

## 6. Rendern
```bash
python S/reel.py --plan reel-arbeit/plan.json
```
Ergebnis: 1080×1920, 30 fps, H.264 mit Originalton.

## 7. Abgeben
Nenne den Pfad der fertigen Datei, liste in 2–4 Zeilen, welche Effekte wo sitzen,
und biete eine Änderung an (z. B. „Karte später?“, „anderer Text?“).

## Hilfreiche Werkzeuge
- Pausen rausschneiden: `python S/schnitt.py -i VIDEO -o reel-arbeit/cut.mp4 --words reel-arbeit/words.json --auto-pausen [--fuellwoerter]`
  → erzeugt `cut.words.json` mit neuen Zeitstempeln. Danach mit `cut.mp4` weiterarbeiten.
- Bestimmte Stellen behalten: `--keep 12.4-31.0 --keep 45-58.5`
- Untertitel-Datei: `python S/srt.py --words reel-arbeit/words.json --out reel-arbeit/untertitel.srt`
- Eigene Farben: `brand.json` im Arbeitsordner (Schlüssel: accent, accent2, green, highlight).

## Wenn etwas hakt
- `faster-whisper` lädt beim ersten Mal ein Sprachmodell (~460 MB für `small`). Ohne Internet: `--model tiny`.
- Sehr lange Videos: erst mit `schnitt.py --keep` kürzen, dann Effekte.
- Rendern ist schnell (~1 s pro Sekunde Video); `tiefen-ui` braucht etwa doppelt so lang.

## Transkript prüfen (wichtig für saubere Untertitel)
Das Modell kennt viele KI-Begriffe (Claude, ChatGPT, MCP, Slash-Befehle …). Trotzdem vor dem Rendern `words.txt`
lesen und falsch erkannte Namen/Fachwörter direkt in `words.json` korrigieren. Eigene Begriffe vorab mitgeben:
`python S/transcribe.py -i VIDEO -o reel-arbeit/words.json --woerter "Lucaidelfino, EcoWise"`

## Texte auf Karten
Keine Emojis oder Sonderzeichen (✓, 🚀) in Karten-/Blasentexten – die Schrift kennt sie nicht, sie werden entfernt.
