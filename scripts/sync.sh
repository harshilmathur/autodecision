#!/bin/bash
# Sync the canonical plugin tree (claude-plugin/) to the legacy install tree (.claude/).
#
# The plugin uses a FLAT commands layout — plugin namespace provides the prefix:
#   claude-plugin/commands/quick.md  →  /autodecision:quick
#
# The legacy install uses a NESTED commands layout — directory name is the namespace:
#   .claude/commands/autodecision/quick.md  →  /autodecision:quick
#
# This script is the single source of truth for that transform. Do not edit .claude/
# directly; edit claude-plugin/ and run this script.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/claude-plugin"
DST="$REPO_ROOT/.claude"

if [ ! -d "$SRC" ]; then
  echo "Error: $SRC not found. Run from a checkout of the autodecision repo." >&2
  exit 1
fi

# Skills tree is identical in both layouts — straight rsync with delete.
mkdir -p "$DST/skills"
rsync -a --delete \
  --exclude='.DS_Store' \
  "$SRC/skills/autodecision/" "$DST/skills/autodecision/"

# Agents tree (team-mode persona definitions) — identical in both layouts.
# Guarded with -d test so this script remains backwards-compatible with branches
# that do not have an agents/ directory yet.
if [ -d "$SRC/agents" ]; then
  mkdir -p "$DST/agents"
  rsync -a --delete \
    --exclude='.DS_Store' \
    "$SRC/agents/" "$DST/agents/"
fi

# Commands tree needs a structural transform: flat plugin-root → nested under autodecision/.
# Wipe the legacy command directory, recreate it, copy each top-level plugin command in.
rm -rf "$DST/commands/autodecision"
mkdir -p "$DST/commands/autodecision"

shopt -s nullglob
for f in "$SRC/commands/"*.md; do
  cp "$f" "$DST/commands/autodecision/$(basename "$f")"
done
shopt -u nullglob

# Count what we wrote so humans can sanity-check.
SKILL_COUNT=$(find "$DST/skills/autodecision" -type f | wc -l | tr -d ' ')
CMD_COUNT=$(find "$DST/commands/autodecision" -type f | wc -l | tr -d ' ')
if [ -d "$DST/agents" ]; then
  AGENT_COUNT=$(find "$DST/agents" -type f | wc -l | tr -d ' ')
else
  AGENT_COUNT=0
fi

echo "Synced claude-plugin/ → .claude/"
echo "  Skills:   $SKILL_COUNT files"
echo "  Agents:   $AGENT_COUNT files"
echo "  Commands: $CMD_COUNT files"
