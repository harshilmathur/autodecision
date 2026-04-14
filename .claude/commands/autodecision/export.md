---
name: autodecision:export
description: Export decision journal, assumptions, and briefs as a portable archive
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# /autodecision:export

Bundle the decision journal, assumption library, and past Decision Briefs into
a single portable markdown file. Useful for sharing with a team, backing up
decision history, or moving to another machine.

## Invocation

```
/autodecision:export                    # Export everything
/autodecision:export --since 2026-01-01 # Export decisions after a date
/autodecision:export --decision pricing-cut-20pct-full  # Export one decision
```

## Execution

### Pre-check: Detect non-journaled runs

Before exporting, scan for runs that have briefs but no journal entries:

```bash
# List all run directories that have a DECISION-BRIEF.md
for dir in ~/.autodecision/runs/*/; do
  slug=$(basename "$dir")
  if [ -f "$dir/DECISION-BRIEF.md" ]; then
    # Check if this slug appears in journal
    if ! grep -q "\"decision_id\":\"$slug\"" ~/.autodecision/journal.jsonl 2>/dev/null; then
      echo "NOT_JOURNALED: $slug"
    fi
  fi
done
```

If non-journaled runs are found, offer to backfill:
> "Found {N} decision runs with briefs but no journal entries: {list slugs}.
> These won't appear in exports or reviews until journaled."
> Options:
> A) Backfill now (I'll create journal entries from the briefs)
> B) Skip — export only journaled decisions

If A: For each non-journaled run, read the DECISION-BRIEF.md and config.json,
construct a minimal journal entry, and append to journal.jsonl.

### Main export

1. Read `~/.autodecision/journal.jsonl` (all journal entries)
2. Read `~/.autodecision/assumptions.jsonl` (all assumptions)
3. For each decision in the journal, read the `DECISION-BRIEF.md` from the run path
4. If `--since` is provided, filter journal entries by timestamp
5. If `--decision` is provided, export only that decision

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

[etc. for each category]

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

7. Write to `~/.autodecision/exports/export-{date}.md`
8. Print the file path and a summary:
   "Exported {N} decisions and {M} assumptions to {path}"

## File Size Management

If the export exceeds 50KB (many decisions with full briefs), offer options:
- A) Full export (all briefs, full detail)
- B) Summary export (journal table + assumption library, brief summaries instead of full briefs)
- C) Single decision export (one brief in full, rest as summaries)
