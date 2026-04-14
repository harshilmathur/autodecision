#!/bin/bash
# Auto-Decision Engine installer
# Usage:
#   ./install.sh                          # Install to ~/.claude (global)
#   ./install.sh ~/.claude                # Same as above, explicit
#   ./install.sh ./your-project/.claude   # Install to a specific project

set -e

TARGET="${1:-$HOME/.claude}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Validate source exists
if [ ! -f "$SCRIPT_DIR/.claude/skills/autodecision/SKILL.md" ]; then
  echo "Error: SKILL.md not found. Run this script from the autodecision repo root."
  exit 1
fi

# Create target directories if needed
mkdir -p "$TARGET/skills" "$TARGET/commands"

# Sync using rsync (idempotent, no nesting, removes stale files)
rsync -a --delete "$SCRIPT_DIR/.claude/skills/autodecision/" "$TARGET/skills/autodecision/"
rsync -a --delete "$SCRIPT_DIR/.claude/commands/autodecision/" "$TARGET/commands/autodecision/"

# Count files installed
SKILL_COUNT=$(find "$TARGET/skills/autodecision" -type f | wc -l | tr -d ' ')
CMD_COUNT=$(find "$TARGET/commands/autodecision" -type f | wc -l | tr -d ' ')

echo "Installed autodecision to $TARGET"
echo "  Skills: $SKILL_COUNT files"
echo "  Commands: $CMD_COUNT files"
echo ""
echo "Restart your Claude Code session to pick up the changes."
