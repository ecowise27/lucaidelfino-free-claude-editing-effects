# Effekt-Katalog (plan.json)

```json
{
  "input": "clip.mov",
  "output": "reel-arbeit/reel.mp4",
  "start": 0, "end": null,
  "effects": [ { "type": "...", "at": 1.2, "until": 4.0, "...": "..." } ]
}
```
`at` / `until` = Sekunden ab `start`. Positionen `x`, `y` = Anteil von Breite/Höhe (0–1).
Farben als Hex (`"#5A3DF5"`), Standard sind Lucas Markenfarben. Bilder/Clips als Pfade.

| type | Wirkung | wichtige Felder |
|---|---|---|
| `untertitel` | Wort-für-Wort-Untertitel | `words`, `style`: `brust` (dezent, Brusthöhe) \| `akzent` (wie brust, Wörter aus `betonen` kursiv-serif in Akzentfarbe, Zahlen farbig) \| `gross` (fett, aktives Wort in Box), `betonen` [Wörter], `y`, `hide` [[a,b]] |
| `titel` | Hook oben | `text`: `"Zeile 1\|Zeile 2"`, `box`: `weiss` (2. Zeile in weißer Box) \| `marke` (Lila-Box) \| `ranking` (orange, kursiv, Großbuchstaben), `color`, `y` (0.15) |
| `glas-chart` | Dunkle Glas-Karte, Kurve klettert, Zahl zählt hoch | `label`, `value`, `prefix`, `suffix` (`"%"`, `" €"`), `decimals`, `points` [0–1], `y` (0.66), `color`, `grow` (s) |
| `schalter` | iOS-Karte, Schalter springen nacheinander an | `items` [3–4 kurze Zeilen], `times` [Sek. je Schalter], `y`, `color` |
| `beweis-karte` | iPhone-Benachrichtigungen stapeln sich über dem Kopf (leicht dahinter) + Zoom | `karten`: [{`app`, `titel`, `text`, `farbe`, `textfarbe`}], `abstand` (0.6 s), `w` (640), `x`, `y` (auto über dem Kopf), `zoom` (0.07), `hinter_kopf` (true) |
| `news-matchcut` (alias `wort-zoom`) | Schnelle Schnitte durch 4 Artikel, Schlüsselwort bleibt an derselben Stelle | `word`, `text` (optional, eigener Artikeltext), `pages` (4), `cut` (0.32 s je Artikel), `color` (`#D62F2F`) |
| `pixel-push` | Jedes Wort groß und lesbar als LED-Pixelschrift, schneller Push zum nächsten | `words` (synchron) oder `text`, `pixel` (7), `color`, `bg`, `y` |
| `glitch-push` | Video wird mit Glitch weggeschoben, großer Satz füllt Screen | `text` (max. ~6 Wörter), `size`, `bg`, `color` |
| `tier-liste` | Tabelle S–F; jedes Element erscheint groß und fällt in seine Reihe | `items`: [{`name`, `tier`, `at`, `bild` (Logo, optional)}], `tiers`, `hold` (1.3 s), `w`, `y` (0.66) |
| `handy-orbit` | Reel-Screens auf einem 3D-Ring, werden Karte für Karte weitergewischt | `images`, `labels`, `count`, `radius`, `swipe` (0.75 s), `dim` (0.3), `y` |
| `tiefen-ui` | UI **hinter** der Person (Freistellung) | `style`: `website` (Browserfenster mit scrollender Aufnahme: `media`, `url`, `w`, `tempo`) \| `panel` (App-Fenster) \| `faecher` (Reel-Karten), `app`, `tabs`, `images`, `labels`, `y`; `profil`: {`name`, `handle`, `zahl`, `zahl_neu`, `button`, `button_neu`, `wechsel_at`, `y` (0.70)} = Kanal-Karte **vor** der Brust |
| `split` | Oben Bild/Video/Grafik, unten Person; Untertitel auf der Trennlinie | `media` (Bild oder Video) **oder** `grafik`: {`typ`: `icon-grid` (`n`, `highlight`, `at`) \| `zahl` (`value`, `prefix`, `suffix`, `label`)}, `ratio` (0.5), `face_y` |
| `preis-tag` | Weißes Preisschild, Zahl springt hoch (26 → 398 → 500 €) | `values` [Zahlen], `times` [Sek.], `prefix`, `suffix` (`" €"`), `x`, `y`, `tilt`, `size` |
| `punch` | Zoom aufs Gesicht für Betonung | `zoom` (1.18), `smooth` (false = harter Schnitt), `cy` |
| `text-hinter-kopf` | Riesiges Wort steigt Buchstabe für Buchstabe **hinter** der Person auf | `text`, `color` / `color2` (Verlauf), `y` (auto: Kopfhöhe), `size` |
| `zoom-durchschnitt` | Rasanter Zoom ins Gesicht (Radial-Blur, RGB-Split), Blitz, Peitschen-Zoom heraus mit Wackler | `at` (= Schnittpunkt), `zoom` (4.0), `cx`, `cy` (0.36) |
| `chat-blasen` | iMessage-artige Nachrichten mit Tipp-Animation | `messages`: [{`text`, `von`: `links`\|`rechts`, `at`}], `y` (0.07), `farbe_rechts` |
| `kommentar-antwort` | Instagram-Sticker „Antwort auf den Kommentar von …“ | `name`, `text`, `y` (0.16) |
| `grosse-worte` | Kinetische Typo: Wörter knallen rein und stapeln sich, Schlüsselwörter in schräger Box | `words` oder `text`, `betonen`, `hintergrund`: `blur`\|`schwarz`\|`marke`, `color` |
| `neon-kontur` | Neon-Doppellinie zeichnet sich um die Person, pulsiert | `color`, `color2`, `dim` (0.45) |
| `klon-echo` | Eingefärbte Klone fächern sich links/rechts auf | `anzahl` (3), `abstand` (230), `farben` [Hex] |
| `freeze-sticker` | Standbild, Person als Sticker mit weißem Rand, Pfeil + Beschriftung | `label`, `seite`: `links`\|`rechts`, `rand` (15), `size`, `color` |
| `magazin-cover` | Roter Rahmen, Titel hinter dem Kopf, Coverzeilen, Barcode | `titel`, `zeilen` [3], `ausgabe`, `color`, `titelfarbe`, `zeilen_y` |
| `ki-scan` | Scan-Linie, Punktraster, Zielklammern am Kopf, Daten tippen sich ein | `zeilen` [2–3], `color` (Mint) |
| `handy-portal` | Video schrumpft in schwebendes iPhone mit 3D-Kippen, dann zurück | `media` (optional), `text`, `kippen` (14°), `uebergang` (0.5 s) |
| `spotlight` | Duotone-Hintergrund, drehende Lichtstrahlen, Randlicht, Person in Farbe | `hell`, `dunkel`, `cx`, `cy` |

## Faustregeln
- Hook (`titel`) in den ersten 0–3 s.
- `beweis-karte`, `glas-chart`, `schalter`, `preis-tag` = Belege und Zahlen → genau auf die Zahl setzen.
- `wort-zoom`, `pixel-push`, `grosse-worte`, `zoom-durchschnitt` = Pattern-Interrupt → alle 6–10 s einer, nie zwei hintereinander.
- `neon-kontur`, `magazin-cover`, `ki-scan`, `text-hinter-kopf` = starke Hooks für die ersten 3 Sekunden.
- `punch` auf jede zweite starke Aussage, 1–3 s lang, wechselnd mit normal.
- `tiefen-ui` braucht ein Video, in dem die Person klar vor dem Hintergrund steht (Kopf und Schultern sichtbar).
- Im Split immer `untertitel` – sie springen automatisch auf die Trennlinie.
| `carousel-spin` | Reels steigen aus dem gefilmten Handy auf einen 3D-Ring und werden gewischt | `images` (Videos/Bilder), `labels`, `hoehe` (430), `radius` (400), `swipe` (0.7), `handy_x`/`handy_y`, `hand_vorne` |
| `koerper-orbit` | Reels kreisen auf einem 3D-Ring um die Person (vorne/hinten) | `images`, `labels`, `y` (0.56), `radius` (470), `speed` (0.14) |
