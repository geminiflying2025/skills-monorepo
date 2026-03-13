#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <skill-name> <target>"
  echo "target: local | <ssh-host>"
  exit 1
fi

SKILL_NAME="$1"
TARGET="$2"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT_DIR/skills/$SKILL_NAME/"

if [ ! -d "$SRC" ]; then
  echo "Skill not found: $SRC"
  exit 1
fi

if [ "$TARGET" = "local" ]; then
  DEST="$HOME/.openclaw/skills/$SKILL_NAME/"
  mkdir -p "$HOME/.openclaw/skills/$SKILL_NAME"
  rsync -av --delete \
    --exclude '.git' \
    --exclude '.DS_Store' \
    --exclude 'node_modules' \
    --exclude '.venv' \
    --exclude 'dist' \
    --exclude '.pytest_cache' \
    "$SRC" "$DEST"
else
  ssh "$TARGET" "mkdir -p ~/.openclaw/skills/$SKILL_NAME"
  rsync -av --delete \
    --exclude '.git' \
    --exclude '.DS_Store' \
    --exclude 'node_modules' \
    --exclude '.venv' \
    --exclude 'dist' \
    --exclude '.pytest_cache' \
    "$SRC" "$TARGET":~/.openclaw/skills/$SKILL_NAME/
fi
