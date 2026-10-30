"""Einmal vor dem ersten Rendern ausführen: prüft und installiert alles Nötige.

  python setup.py            # Basis: Pillow, numpy, ffmpeg, faster-whisper
  python setup.py --tiefe    # zusätzlich MediaPipe (für tiefen-ui: Person freistellen)
"""
import importlib
import shutil
import subprocess
import sys


def pip(*pkgs):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *pkgs], check=False)


def have(mod):
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


need = [("PIL", "pillow"), ("numpy", "numpy"), ("fontTools", "fonttools"), ("faster_whisper", "faster-whisper")]
if "--tiefe" in sys.argv:
    need.append(("mediapipe", "mediapipe"))
missing = [p for m, p in need if not have(m)]
if missing:
    print("Installiere:", ", ".join(missing))
    pip(*missing)
if not shutil.which("ffmpeg"):
    print("Kein ffmpeg im System → installiere imageio-ffmpeg (bringt ffmpeg mit)")
    pip("imageio-ffmpeg")
ok = all(have(m) for m, _ in need)
print("✓ Bereit" if ok else "⚠ Einige Pakete fehlen noch – Netzwerkzugriff auf pypi.org prüfen")
