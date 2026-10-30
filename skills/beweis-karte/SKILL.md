---
name: beweis-karte
description: Beweis-Stapel: Echte iPhone-Benachrichtigungen (Zahlung erhalten, neue Follower, neuer Termin …) landen nacheinander über dem Kopf und stapeln sich – leicht hinter der Person, Kamera zoomt heran.
---

# /beweis-karte

Wie wenn das Handy während des Redens Erfolge meldet: weiße iOS-Benachrichtigungen fallen ein, die älteren rutschen nach oben, die Person steht davor.

Die gemeinsame Engine heißt `ki-editing-engine` (im Text `S`). Nimm den ersten Pfad, der existiert:
1. `${CLAUDE_PLUGIN_ROOT}/ki-editing-engine` (als Plugin installiert)
2. `ki-editing-engine` im aktuellen Projektordner (GitHub-Vorlage, z. B. Code-Tab am Handy)
3. `~/.claude/ki-editing-engine` (per Installationsskript installiert)
Lies zuerst `S/ABLAUF.md` (Schritte 1–7) und für alle Felder `S/EFFEKTE.md`.

## So gehst du vor
Vorher `python S/setup.py --tiefe` (Freistellung der Person). `karten` = 2–3 Benachrichtigungen passend zum Video ({app, titel, text, textfarbe}). Für `app` gibt es echte Logos: Stripe, PayPal, Shopify, Instagram, TikTok, YouTube, Facebook, LinkedIn, X, WhatsApp, Telegram, Gmail, Kalender (Google), Calendly, Zoom, Google Meet, Slack, Notion, HubSpot, Mailchimp, Claude, ChatGPT, Canva, Figma, Spotify, Apple, Airbnb – andere Namen bekommen ein Buchstaben-Icon, `abstand` (Sek. zwischen den Karten). Ohne Angabe: Zahlung / Follower / Termin.

## Plan-Vorlage
```json
{
  "input": "VIDEO",
  "output": "reel-arbeit/reel.mp4",
  "effects": [
    {
      "type": "beweis-karte",
      "at": 1.0,
      "until": 4.5,
      "karten": [
        {
          "app": "Stripe",
          "titel": "Zahlung erhalten",
          "text": "+ 1.250,00 €",
          "farbe": "#635BFF"
        },
        {
          "app": "Instagram",
          "titel": "Neue Follower",
          "text": "+ 2.400 heute",
          "farbe": "#E1306C"
        }
      ]
    }
  ]
}
```

## Worauf achten
Nur reale oder klar als Beispiel erkennbare Zahlen verwenden.
