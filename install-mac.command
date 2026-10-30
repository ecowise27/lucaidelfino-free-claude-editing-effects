#!/bin/bash
# KI-Editing-Pack für Claude Code installieren (Mac)
cd "$(dirname "$0")"
mkdir -p "$HOME/.claude/skills"
for d in skills/*/; do
  name=$(basename "$d")
  rm -rf "$HOME/.claude/skills/$name"
  cp -R "$d" "$HOME/.claude/skills/$name"
done
rm -rf "$HOME/.claude/ki-editing-engine"
cp -R ki-editing-engine "$HOME/.claude/ki-editing-engine"
echo ""
echo "✓ KI-Editing-Pack installiert nach ~/.claude/skills"
echo "  Claude Code neu starten, dann / tippen."
read -n 1 -s -r -p "Taste drücken zum Schließen …"
