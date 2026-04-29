#!/usr/bin/env bash
#
# sync-check-opencode.sh — validate the .opencode/ tree is structurally sound.
#
# Unlike sync.sh (which mirrors claude-plugin/ → .claude/), .opencode/ has no
# upstream — it IS the source of truth for OpenCode-specific glue. This check
# validates the files are present and structurally consistent.
#
# Exit 0: ok. Non-zero: something is missing or malformed.
#
# Runs in CI via .github/workflows/sync-check.yml (optional — low priority since
# failures here are authoring errors, not silent drift).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPENCODE="$ROOT/.opencode"
FAIL=0

fail() {
  echo "FAIL: $*" >&2
  FAIL=1
}

ok() {
  echo "  ok: $*"
}

echo "Checking .opencode/ tree at $OPENCODE"

# ── 1. Required directories ──────────────────────────────────────────────────
for dir in commands agents; do
  if [[ ! -d "$OPENCODE/$dir" ]]; then
    fail "missing directory .opencode/$dir/"
  else
    ok ".opencode/$dir/ exists"
  fi
done

# ── 2. host-adapter.md present ───────────────────────────────────────────────
if [[ ! -f "$OPENCODE/host-adapter.md" ]]; then
  fail "missing .opencode/host-adapter.md (required — every command references it)"
else
  ok ".opencode/host-adapter.md exists"
fi

# ── 3. All 10 commands ───────────────────────────────────────────────────────
EXPECTED_COMMANDS=(
  autodecision
  autodecision-quick
  autodecision-compare
  autodecision-revise
  autodecision-challenge
  autodecision-summarize
  autodecision-publish
  autodecision-plan
  autodecision-review
  autodecision-export
)

for cmd in "${EXPECTED_COMMANDS[@]}"; do
  f="$OPENCODE/commands/${cmd}.md"
  if [[ ! -f "$f" ]]; then
    fail "missing command file .opencode/commands/${cmd}.md"
    continue
  fi

  # Frontmatter must have a description
  if ! head -20 "$f" | grep -qE '^description:'; then
    fail "command $cmd missing 'description:' frontmatter"
  fi

  # Frontmatter must NOT have subtask: true (orchestrators must be primary)
  if head -20 "$f" | grep -qE '^subtask:[[:space:]]*true'; then
    fail "command $cmd has forbidden 'subtask: true' — orchestrators must run as primary session"
  fi

  # Every command must reference host-adapter.md
  if ! grep -q 'host-adapter.md' "$f"; then
    fail "command $cmd does not reference .opencode/host-adapter.md (should read it on bootstrap)"
  fi

  # Every command must reference the skill path
  if ! grep -qE '\.claude/skills/autodecision/' "$f"; then
    fail "command $cmd does not reference the skill at .claude/skills/autodecision/"
  fi

  ok "command $cmd"
done

# ── 4. All 9 agents ──────────────────────────────────────────────────────────
EXPECTED_AGENTS=(
  ad-optimist
  ad-pessimist
  ad-competitor
  ad-regulator
  ad-customer
  ad-critique
  ad-adversary
  ad-sensitivity
  ad-decide
)

for agent in "${EXPECTED_AGENTS[@]}"; do
  f="$OPENCODE/agents/${agent}.md"
  if [[ ! -f "$f" ]]; then
    fail "missing agent file .opencode/agents/${agent}.md"
    continue
  fi

  # Must be mode: subagent
  if ! head -20 "$f" | grep -qE '^mode:[[:space:]]*subagent'; then
    fail "agent $agent missing 'mode: subagent' frontmatter"
  fi

  # Must be hidden (out of @ autocomplete — avoid user invoking them directly)
  if ! head -20 "$f" | grep -qE '^hidden:[[:space:]]*true'; then
    fail "agent $agent should have 'hidden: true' in frontmatter"
  fi

  ok "agent $agent"
done

# ── 5. Skill is discoverable ─────────────────────────────────────────────────
SKILL="$ROOT/.claude/skills/autodecision/SKILL.md"
if [[ ! -f "$SKILL" ]]; then
  fail "skill not found at .claude/skills/autodecision/SKILL.md — run ./scripts/sync.sh first"
else
  ok "skill discoverable at .claude/skills/autodecision/"
fi

# ── 6. Validator script is reachable ─────────────────────────────────────────
VALIDATOR="$ROOT/.claude/skills/autodecision/scripts/validate-brief.py"
if [[ ! -f "$VALIDATOR" ]]; then
  fail "validate-brief.py not found under the synced skill — run ./scripts/sync.sh"
else
  ok "validate-brief.py discoverable"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
if [[ $FAIL -ne 0 ]]; then
  echo
  echo "sync-check-opencode: FAILED"
  exit 1
fi

echo
echo "sync-check-opencode: PASSED"
