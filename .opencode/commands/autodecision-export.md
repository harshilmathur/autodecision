---
description: Export decision journal, assumptions, and briefs as a portable markdown archive
agent: build
---

# /autodecision-export

Bundle the decision journal, assumption library, and past Decision Briefs into a single portable markdown file. For sharing with a team, backing up history, or moving to another machine.

Run on: $ARGUMENTS

## Usage

```
/autodecision-export                              # Export everything
/autodecision-export --since 2026-01-01           # Export decisions after a date
/autodecision-export --decision {slug}            # Export one decision
```

## Bootstrap

Read via `read`:
1. `.claude/skills/autodecision/SKILL.md`
2. `.opencode/host-adapter.md`
3. `.claude/skills/autodecision/references/journal-spec.md`
4. `.claude/skills/autodecision/references/assumption-library-spec.md`

## Pre-Check: Detect Non-Journaled Runs

Before exporting, scan for runs that have briefs but no journal entries. Via `bash`:

```bash
for dir in ~/.autodecision/runs/*/; do
  slug=$(basename "$dir")
  if [ -f "$dir/DECISION-BRIEF.md" ]; then
    if ! grep -q "\"decision_id\":\"$slug\"" ~/.autodecision/journal.jsonl 2>/dev/null; then
      echo "NOT_JOURNALED: $slug"
    fi
  fi
done
```

If any non-journaled runs are found, use `question` to offer:

> Found {N} decision runs with briefs but no journal entries: {list slugs}.
> These won't appear in exports or reviews until journaled.
> Options:
>   A) Backfill now (I'll create journal entries from the briefs)
>   B) Skip — export only journaled decisions

If A: for each non-journaled run, read `DECISION-BRIEF.md` and `config.json`, construct a minimal journal entry (extract decision_statement, recommendation, confidence from the brief), and append to `journal.jsonl`. Document that the entry was `backfilled: true` in the entry itself.

## Main Export

1. Read `~/.autodecision/journal.jsonl` (all entries).
2. Read `~/.autodecision/assumptions.jsonl` (all assumptions).
3. For each decision in the journal, read the `DECISION-BRIEF.md` from its `run_path`.
4. If `--since` is provided, filter by timestamp.
5. If `--decision` is provided, export only that decision.

6. Assemble into a single markdown file:

```markdown
# Auto-Decision Engine Export

Exported: {date}
Decisions: {count}
Assumptions tracked: {count}

---

## Decision Journal

| # | Decision | Date | Mode | Confidence | Recommendation | Outcome |
|---|----------|------|------|------------|----------------|---------|
{one row per decision}

---

## Assumption Library

### By Category

#### Market Assumptions
| Assumption | Times Used | Held | Broke | Untested | Last Validated |
|-----------|-----------|------|-------|----------|----------------|
{rows}

#### Competition Assumptions
{rows}

#### Execution Assumptions
{rows}

#### Financial Assumptions
{rows}

#### Customer Assumptions
{rows}

#### Regulatory Assumptions
{rows}

### Most Reliable Assumptions (held > 2x, never broke)
{list}

### Least Reliable Assumptions (broke > 1x)
{list}

---

## Decision Briefs

### 1. {decision_statement} ({date})

{full DECISION-BRIEF.md content}

---

### 2. {next decision}

{brief content}
```

7. Write to `~/.autodecision/exports/export-{YYYY-MM-DD}.md` (create the `exports/` directory via `bash` if missing).

8. Print the file path and a summary:
   `"Exported {N} decisions and {M} assumptions to {path} ({size} KB)"`

## File Size Management

If the export exceeds 50KB (many decisions with full briefs), use `question` to offer:
- A) Full export (all briefs, full detail)
- B) Summary export (journal table + assumption library, brief summaries instead of full briefs)
- C) Single decision export (one brief in full, rest as summaries) — then ask which decision

## Rules

- Never writes outside `~/.autodecision/exports/`.
- Never auto-sends or auto-publishes the export. User copies it manually.
- Preserves source tags in the included briefs — never strips `[G#]`, `[D#]`, `[U#]`, `[C#:persona]`.
- If `assumptions.jsonl` is empty, skip the Assumption Library section entirely — don't emit empty tables.
