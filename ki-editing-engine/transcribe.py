"""Transkription mit Wort-Zeitstempeln (faster-whisper, läuft lokal, kein API-Key).

Aufruf:
  python transcribe.py --input clip.mp4 --out words.json [--model small] [--lang de]

Schreibt:
  words.json      – [{"w": "Wort", "s": 1.23, "e": 1.51}, ...]
  words.txt       – lesbares Transkript mit Zeitmarken (für Claude zum Planen)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def ensure_whisper():
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "faster-whisper"], check=True)


def load_audio(path: str):
    """Audio per ffmpeg als 16-kHz-Mono-Array lesen (unabhängig von PyAV-Versionen)."""
    import numpy as np

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from reelkit import ffmpeg_bin

    raw = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


# Fachbegriffe, die das Modell sonst falsch schreibt (per --woerter erweiterbar)
VOKABULAR = ("Claude, ChatGPT, Gemini, Midjourney, Higgsfield, ElevenLabs, MCP, MCPs, Konnektoren, KI, Prompt, Prompts, "
             "Slash-Befehle, Social Media, Social-Media-Bereich, Reels, Instagram, TikTok, YouTube, n8n, Notion, Canva, "
             "Agenten, Automationen, Workflow, Hacks, Luca, EcoWise")

KORREKTUR = {"klod": "Claude", "klot": "Claude", "cloud": "Claude", "chat-gbt": "ChatGPT", "chat-gpt": "ChatGPT",
             "chatgbt": "ChatGPT", "tschätschipiti": "ChatGPT", "befäle": "Befehle", "slash-befäle": "Slash-Befehle"}


def correct(words: list[dict]) -> list[dict]:
    for w in words:
        core = w["w"].rstrip(".,!?")
        tail = w["w"][len(core):]
        fix = KORREKTUR.get(core.lower())
        if fix:
            w["w"] = fix + tail
    return words


def transcribe(path: str, model: str = "small", lang: str | None = "de", woerter: str = "") -> list[dict]:
    ensure_whisper()
    from faster_whisper import WhisperModel

    try:
        m = WhisperModel(model, device="cpu", compute_type="int8")
    except Exception as e:  # meist: Modell-Download blockiert
        sys.exit(f"Sprachmodell '{model}' konnte nicht geladen werden ({e.__class__.__name__}).\n"
                 "→ Netzwerkzugriff auf huggingface.co erlauben (Einstellungen der Code-Ausführung bzw. Cloud-Umgebung)\n"
                 "→ oder kleineres Modell testen: --model tiny")
    prompt = VOKABULAR + (", " + woerter if woerter else "")
    segments, _ = m.transcribe(load_audio(path), language=lang, word_timestamps=True, vad_filter=True, initial_prompt=prompt)
    words = []
    for seg in segments:
        for w in seg.words or []:
            txt = w.word.strip()
            if not txt:
                continue
            # "1" + ".284" → "1.284", angehängte Satzzeichen zum vorherigen Wort
            if words and (re.match(r"^[.,]\d", txt) and words[-1]["w"][-1:].isdigit() or re.fullmatch(r"[.,!?;:%€]+", txt)
                          or txt.startswith("-")):
                words[-1]["w"] += txt
                words[-1]["e"] = round(w.end, 3)
                continue
            words.append({"w": txt, "s": round(w.start, 3), "e": round(w.end, 3)})
    return correct(words)


def to_text(words: list[dict]) -> str:
    """Zeilen à ca. 8 Wörter mit Startzeit – leicht zu lesen und zu zitieren."""
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 8 or w["w"].endswith((".", "!", "?")):
            lines.append(f"[{cur[0]['s']:6.2f}–{cur[-1]['e']:6.2f}] " + " ".join(x["w"] for x in cur))
            cur = []
    if cur:
        lines.append(f"[{cur[0]['s']:6.2f}–{cur[-1]['e']:6.2f}] " + " ".join(x["w"] for x in cur))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True)
    ap.add_argument("--out", "-o", default="words.json")
    ap.add_argument("--model", default="small", help="tiny | base | small | medium (größer = genauer, langsamer)")
    ap.add_argument("--lang", default="de")
    ap.add_argument("--woerter", default="", help="Zusätzliche Namen/Fachbegriffe, kommagetrennt (z. B. 'Lucaidelfino, Fluxomate')")
    a = ap.parse_args()
    words = transcribe(a.input, a.model, a.lang or None, a.woerter)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(words, ensure_ascii=False, indent=0))
    txt = to_text(words)
    Path(a.out).with_suffix(".txt").write_text(txt)
    print(txt)
    print(f"\n{len(words)} Wörter → {a.out}")


if __name__ == "__main__":
    main()
