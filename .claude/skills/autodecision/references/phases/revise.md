# Phase: REVISE

## Purpose

Revise a previous decision with changed assumptions, new hypotheses, new data, or a
different tilt. One natural language input. The system parses what changed, re-runs
from the earliest affected phase, and produces both a standalone brief and a diff.

## Invocation

```
/autodecision:revise {slug} "{what changed}"
```

## Progress Template

```
Revise: Load original run                        [pending]
Revise: Parse and classify changes                [pending]
Revise: Confirm understanding with user           [pending]
Revise: Prepare revised run directory             [pending]
Revise: Simulate with revised inputs              [pending]
Revise: Generate Decision Brief                   [pending]
Revise: Generate Revision Diff                    [pending]
Revise: Persist to journal                        [pending]
```

## Step 1: LOAD

Read the original run's full state from `~/.autodecision/runs/{slug}/`:

- `config.json` (decision statement, sub-questions, constraints, tilt)
- `ground-data.md` (grounding research)
- `user-inputs.md` (if exists)
- Latest iteration's `hypotheses.json`
- Latest iteration's `effects-chains.json` (the converged effects map)
- `sensitivity.json` (assumption sensitivity rankings)
- `DECISION-BRIEF.md` (the original recommendation)

If the slug doesn't exist, tell the user and list available runs:
```bash
ls ~/.autodecision/runs/
```

## Step 2: PARSE

Parse the user's natural language revision input. Classify into one or more change types:

### Change Type Detection

Read the original run's `all_assumptions` map from effects-chains.json and the
hypothesis list from hypotheses.json. Use these as the vocabulary to match against.

| Pattern in User Input | Change Type | Example |
|----------------------|-------------|---------|
| "What if {assumption} is {value}" | ASSUMPTION_OVERRIDE | "What if attach rate is only 8%" |
| "Assume {fact}" | ASSUMPTION_OVERRIDE | "Assume Competitor A reaches parity in 6 months" |
| "Add hypothesis: {description}" | NEW_HYPOTHESIS | "Add: partner with Orchestrator Co for free UPI" |
| "Remove/eliminate/drop H{N}" | REMOVE_HYPOTHESIS | "Eliminate H2, it's off the table" |
| "New data: {fact}" | NEW_DATA | "Competitor A hired 5 ex-Acme Corp engineers" |
| "Change tilt to {tilt}" | TILT_CHANGE | "Change tilt to risk minimization" |
| "{constraint} changed to {value}" | CONSTRAINT_CHANGE | "IPO is now in 3 months" |
| Multiple statements | COMBINED | "What if attach is 8% AND Competitor A matches in 6 months" |

### Earliest Affected Phase

| Change Type | Re-run From | Reuses From Original |
|-------------|------------|---------------------|
| ASSUMPTION_OVERRIDE | Phase 3 (SIMULATE) | config, ground-data, hypotheses |
| NEW_HYPOTHESIS | Phase 2 (HYPOTHESIZE) | config, ground-data |
| REMOVE_HYPOTHESIS | Phase 2 (HYPOTHESIZE) | config, ground-data |
| NEW_DATA | Phase 1 (GROUND) — append to ground-data | config |
| TILT_CHANGE | Phase 3 (SIMULATE) | config (with new tilt), ground-data, hypotheses |
| CONSTRAINT_CHANGE | Phase 2 (HYPOTHESIZE) | config (with new constraints), ground-data |
| COMBINED | Earliest of individual types | Everything before that phase |

## Step 3: CONFIRM

Show the user what was parsed. Use AskUserQuestion:

> "I understood your revision as:
> - [list each parsed change with specific values]
> - Re-running from: Phase {N} ({phase name})
> - Reusing from original: {list of reused artifacts}
> - Running: 1 iteration (medium mode) with 5 persona council
>
> Does this look right?"
>
> Options:
> A) Correct, proceed
> B) I meant something different (explain)

If B: ask the user to clarify, re-parse, re-confirm.

## Step 4: PREPARE

Create the revision run directory:

```bash
# Find next revision number
N=1
while [ -d ~/.autodecision/runs/{slug}-revise-$N ]; do N=$((N+1)); done
mkdir -p ~/.autodecision/runs/{slug}-revise-$N/iteration-1/council
```

Copy reusable files from the original run:

- **Always copy:** `config.json`, `ground-data.md`
- **Copy if re-running from Phase 3+:** `hypotheses.json` (from latest iteration)
- **Never copy:** effects-chains.json, council/*.json, critique, adversary, sensitivity (these will be regenerated)

Modify copied files to reflect the changes:

- **ASSUMPTION_OVERRIDE:** Add a `revision_overrides` section to shared-context.md that
  tells personas "For this revision, assume {X} instead of {Y}. All other assumptions
  from the original analysis remain."
- **NEW_HYPOTHESIS:** Append the new hypothesis to hypotheses.json with a new ID.
- **REMOVE_HYPOTHESIS:** Remove the hypothesis from hypotheses.json.
- **TILT_CHANGE:** Update config.json tilt field.
- **CONSTRAINT_CHANGE:** Update config.json constraints.
- **NEW_DATA:** Append to ground-data.md under a "## Revision Data" section.

## Step 5: EXECUTE

Run from the earliest affected phase using the standard engine protocol.

Key differences from a fresh run:
- **Skip ELICIT.** The user's revision IS the input.
- **Skip GROUND** (unless change type is NEW_DATA, which appends to ground-data).
- **1 iteration only** (medium mode). No convergence loop. This is a what-if exploration.
- **Persona prompts include revision context.** Shared-context.md says:
  "This is a REVISION of a previous analysis. The original recommended {X}.
  The following has changed: {list changes}. Analyze the decision with these
  changes applied. Focus on how the changes affect the recommendation."
- **Use the standard persona council** (5 personas, parallel foreground agents).
- **Run the standard post-simulation pipeline** (synthesis + critique + adversary in
  parallel, then sensitivity, then decide). But only 1 iteration.

## Step 6: PRODUCE OUTPUT

Write TWO files to the revision run directory:

### File 1: DECISION-BRIEF.md

A full standalone Decision Brief using the standard output-format.md template.
A reader should understand this brief WITHOUT reading the original.

Add a header note: "This is a revised analysis. Original run: {slug}. Changes: {list}."

Follow ALL the standard brief rules including human-readable output (no snake_case).

### File 2: REVISION-DIFF.md

A comparison document:

```markdown
# Revision Diff: {decision statement}

**Original run:** {slug} | **Revision:** {slug}-revise-{N}
**Changes applied:** {list of changes in plain English}
**Date:** {date}

---

## Recommendation Comparison

| Dimension | Original | Revised |
|-----------|----------|---------|
| Recommendation | {original action} | {revised action} |
| Confidence | {original} | {revised} |
| Leading hypothesis | {original} | {revised} |
| Tilt | {original} | {revised} |

## Did the Recommendation Change?

{YES: explain what specifically flipped it. Which assumption or hypothesis was load-bearing?}
{NO: the original recommendation is robust to this scenario. Explain why.}

## Effects That Shifted (probability change > 0.10)

| Effect | Original P | Revised P | Shift | Why |
|--------|-----------|-----------|-------|-----|
| {human-readable description} | {P} | {P} | {delta} | {which change caused this shift} |

## Assumptions That Changed State

| Assumption | Original | Revised | Impact |
|-----------|----------|---------|--------|
| {description} | {SOLID/SHAKEABLE/FRAGILE} | {new state} | {what this means} |

## New Effects (not in original)

{Effects that appeared only under the revised scenario}

## Removed Effects (in original, gone in revised)

{Effects that disappeared under the revised scenario}

## Hypotheses Status Change

| Hypothesis | Original Status | Revised Status |
|-----------|----------------|----------------|
| {H1} | {status} | {status} |

## Bottom Line

{2-3 sentence summary: Is the original recommendation robust to this revision?
If it flipped, what is the minimum change that would flip it back?
What does this tell the decision-maker about the sensitivity of their strategy?}
```

## Step 7: PERSIST

Append a revision entry to `~/.autodecision/journal.jsonl`:

```json
{
  "decision_id": "{slug}-revise-{N}",
  "original_decision_id": "{slug}",
  "type": "revision",
  "revision_input": "{user's natural language input}",
  "changes_applied": ["change 1", "change 2"],
  "recommendation_changed": true/false,
  "original_recommendation": "{original}",
  "revised_recommendation": "{revised}",
  "timestamp": "...",
  ...standard journal fields...
}
```

Print to user: "Revision complete. Brief at {path}. Diff at {path}."
If recommendation changed: "The revision FLIPPED the recommendation. Consider running
a full `/autodecision` to validate the new direction."
If recommendation held: "The original recommendation is robust to this scenario."

## Step 8: OFFER EXPORT

After printing, offer to export to current working directory:

> "Export revision outputs to current directory?"
> Options: A) Export brief + diff  B) Export brief only  C) Skip

If A:
```bash
cp ~/.autodecision/runs/{slug}-revise-{N}/DECISION-BRIEF.md ./{slug}-revise-{N}-DECISION-BRIEF.md
cp ~/.autodecision/runs/{slug}-revise-{N}/REVISION-DIFF.md ./{slug}-revise-{N}-REVISION-DIFF.md
```

If B:
```bash
cp ~/.autodecision/runs/{slug}-revise-{N}/DECISION-BRIEF.md ./{slug}-revise-{N}-DECISION-BRIEF.md
```
