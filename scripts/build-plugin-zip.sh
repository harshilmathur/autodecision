#!/bin/bash
# build-plugin-zip.sh — produce a Claude plugin zip suitable for manual upload
# (Cowork custom plugin uploader, offline install, distributing to teammates who
# can't run /plugin marketplace add).
#
# Cowork's uploader rejects any zip that does not have .claude-plugin/plugin.json
# at the ARCHIVE ROOT. macOS Finder's "Compress" on the claude-plugin/ folder
# produces claude-plugin/.claude-plugin/plugin.json inside the zip — nested one
# level — and Cowork rejects it with:
#
#   Invalid plugin: missing .claude-plugin/plugin.json
#
# This script zips the *contents* of claude-plugin/ (not the directory itself),
# so plugin.json lands at the zip root. It also strips .DS_Store.
#
# Usage:
#   ./scripts/build-plugin-zip.sh                      # → dist/autodecision-<version>.zip
#   ./scripts/build-plugin-zip.sh /tmp/out.zip         # → custom output path
#
# The version is read from claude-plugin/.claude-plugin/plugin.json.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/claude-plugin"

if [ ! -f "$PLUGIN_DIR/.claude-plugin/plugin.json" ]; then
  echo "Error: $PLUGIN_DIR/.claude-plugin/plugin.json not found." >&2
  echo "Run this script from a clean clone of the autodecision repo." >&2
  exit 1
fi

# Extract version from plugin.json (pure bash, no jq dependency).
VERSION=$(grep -E '"version"[[:space:]]*:' "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  | head -1 \
  | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')

if [ -z "$VERSION" ]; then
  echo "Error: could not parse version from plugin.json" >&2
  exit 1
fi

OUTPUT="${1:-$REPO_ROOT/dist/autodecision-$VERSION.zip}"
OUTPUT_DIR="$(dirname "$OUTPUT")"
mkdir -p "$OUTPUT_DIR"

# Remove any prior zip at the same path so `zip` doesn't append to it.
rm -f "$OUTPUT"

# cd INTO claude-plugin/ and zip "." so .claude-plugin/plugin.json lands at zip root.
# -r recurse, -X strip extra file attributes (smaller, more reproducible zips),
# -x exclude .DS_Store anywhere in the tree.
cd "$PLUGIN_DIR"
zip -rX "$OUTPUT" . -x "*.DS_Store" "**/.DS_Store" >/dev/null

# Sanity-check: `.claude-plugin/plugin.json` must exist at the archive root.
# `unzip -Z1` prints one filename per line with no header, so an exact match
# catches both missing and nested-under-wrapper-folder cases. Capture the list
# to a variable first — piping `unzip | grep -q` trips `set -o pipefail` when
# grep closes the pipe early on the first match (SIGPIPE on unzip).
ENTRIES="$(unzip -Z1 "$OUTPUT")"
if ! printf '%s\n' "$ENTRIES" | grep -qxF ".claude-plugin/plugin.json"; then
  echo "Error: built zip is missing .claude-plugin/plugin.json at root." >&2
  echo "Cowork (and any plugin manifest-checker) will reject this. Aborting." >&2
  echo "--- zip entries (first 10): ---" >&2
  printf '%s\n' "$ENTRIES" | head -10 >&2
  rm -f "$OUTPUT"
  exit 1
fi

SIZE=$(wc -c < "$OUTPUT" | tr -d ' ')
FILE_COUNT=$(unzip -l "$OUTPUT" | tail -1 | awk '{print $2}')

echo "Built $OUTPUT"
echo "  Version:  $VERSION"
echo "  Size:     $(echo "$SIZE" | awk '{printf "%.1f KB", $1/1024}')"
echo "  Files:    $FILE_COUNT"
echo ""
echo "In Cowork: Customize → Create plugin → Upload plugin → select this file."
