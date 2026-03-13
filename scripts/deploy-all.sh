#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <target>"
  echo "target: local | <ssh-host>"
  exit 1
fi

TARGET="$1"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$ROOT_DIR/skills"

for skill_path in "$SKILLS_DIR"/*; do
  [ -d "$skill_path" ] || continue
  skill_name="$(basename "$skill_path")"
  echo "==> Deploying $skill_name to $TARGET"
  "$ROOT_DIR/scripts/deploy-skill.sh" "$skill_name" "$TARGET"
done
