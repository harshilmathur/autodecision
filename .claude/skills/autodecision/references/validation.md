# Output Validation Rules

This file defines validation rules applied by the orchestrator AFTER each phase
writes output. One file, one set of rules, applied everywhere. This ensures
consistent output across different models (Opus, Sonnet, Haiku) and systems.

The orchestrator reads this file once at run start and applies the relevant checks
after each phase completes.

## When to Validate

After EVERY phase that writes a JSON file. Read the file back, apply the rules
below, fix what can be fixed automatically, reject and re-prompt what can't.

## Rule 0: JSON Syntax Validity

**Applies to:** ALL JSON output files, BEFORE any semantic validation.

This is the first gate. If a file doesn't parse, no other rule can run and
downstream synthesis breaks. Trailing commas are the most common LLM leak —
persona subagents emit JS-style object literals instead of strict JSON.

```
STEP 1: Parse the file. Use `jq . {file}` or read + JSON.parse.

STEP 2: If parse fails, apply auto-fixes in this order, re-parsing after each:
  a. Strip trailing commas before ] or }
       Regex: `,(\s*[\]}])` → `\1`
  b. Strip // line comments and /* ... */ block comments
  c. Convert single-quoted string literals to double-quoted
       (only if the string has no unescaped double quotes inside)
  d. Strip any text before the first `{` or `[` and after the last matching `}` or `]`

STEP 3: If parse STILL fails, reject and re-prompt the agent exactly once:
  "Your JSON output failed to parse at line {N}: {parser error}.
  Emit only strict, parseable JSON — no trailing commas, no comments,
  no single quotes, no trailing text. Re-emit the full output."

STEP 4: If second attempt also fails:
  - Exclude this file from downstream phases
  - Log: "Persona {name} excluded: unparseable JSON after retry"
  - Synthesis continues with the remaining personas
  - Note the exclusion in the Decision Brief header
```

**NEVER:** silently swallow parse errors. A file that doesn't parse is a broken
persona; the brief must note which persona was excluded so the reader knows the
council ran with fewer than 5 voices.

**Common failure examples:**
```
// trailing comma after last effect
{"effects": [
  {"effect_id": "a"},
  {"effect_id": "b"},   ← trailing comma breaks parse
]}

// JS-style comments
{
  // probability is median
  "probability": 0.65
}

// single quotes
{'effect_id': 'a'}  ← must be double quotes
```

## Rule 1: Probability Format

**Applies to:** All `probability` fields in persona outputs and effects-chains.json

```
VALID: 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
       0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95

AUTO-FIX:
  "70%" → 0.70
  0.7 → 0.70
  0.333 → 0.35 (round to nearest 0.05)
  "high" → reject (cannot coerce qualitative to number)

REJECT IF: value is a non-numeric string (e.g., "high", "likely", "probable")
```

## Rule 2: Effect ID Format

**Applies to:** All `effect_id` fields

```
PATTERN: ^[a-z][a-z0-9_]{0,29}$
  - Lowercase only
  - Snake_case
  - Max 30 characters
  - Must start with a letter

AUTO-FIX:
  "ACQ_INCREASE" → "acq_increase" (lowercase)
  "acqIncrease" → "acq_increase" (camelCase to snake_case)
  "acquisition rate acceleration" → "acquisition_rate_accel" (spaces to underscores, truncate)
  "Acq-Increase" → "acq_increase" (dashes to underscores, lowercase)

REJECT IF: after auto-fix, still doesn't match pattern
```

## Rule 3: Assumption Key Format

**Applies to:** All assumption keys in `assumptions` arrays and `all_assumptions` map

```
SAME RULES AS EFFECT ID (Rule 2):
  - Lowercase snake_case
  - Max 50 characters
  - Same auto-fix rules

ADDITIONAL: After synthesis, verify every key in any effect's `assumptions` array
exists in `all_assumptions`. If missing, create a stub entry with description
inferred from the key name.
```

## Rule 4: JSON Field Types

**Applies to:** All JSON output files

```
FIELD TYPE ENFORCEMENT:

| Field | Required Type | Auto-fix |
|-------|--------------|----------|
| effect_id | string | — |
| description | string, min 10 chars | — |
| order | integer (1 or 2) | "1" → 1, 1.0 → 1 |
| probability | float (0.05-0.95) | See Rule 1 |
| probability_range | [float, float] | — |
| council_agreement | integer (1-5) | "4/5" → 4, 4.0 → 4 |
| timeframe | string (enum) | See Rule 5 |
| assumptions | array of strings | null → [] |
| children | array of effects | null → [] |
| parent_effect_id | string (2nd-order only) | — |
| status | "complete" or "partial" | missing → "complete" |
| hypothesis_id | string (h{N}_{desc}) | See Rule 6 |

REJECT IF: field is present but wrong type AND cannot be auto-fixed
```

## Rule 5: Timeframe Enum

**Applies to:** All `timeframe` fields

```
VALID VALUES: "immediate", "0-3 months", "3-6 months", "6-12 months", "12+ months"

AUTO-FIX MAP:
  "0-3m", "0-3mo", "quarterly", "<3 months", "within 3 months" → "0-3 months"
  "3-6m", "3-6mo", "within 6 months" → "3-6 months"
  "6-12m", "6-12mo", "within 12 months" → "6-12 months"
  "1+ years", "12m+", "long-term", "18+ months", "24+ months" → "12+ months"
  "now", "instant", "day 1" → "immediate"

REJECT IF: cannot map to a valid value
```

## Rule 6: Hypothesis ID Format

**Applies to:** All `hypothesis_id` fields

```
PATTERN: ^h\d+_[a-z_]{1,30}$

VALID: h1_price_growth, h2_competitor_response, h3_minimal_impact
INVALID: hypothesis_1, H1_price_growth, pricing_scenario

AUTO-FIX:
  "hypothesis_1" → "h1_hypothesis"
  "H1_Price_Growth" → "h1_price_growth"
  "pricing scenario" → "h1_pricing_scenario" (assign next available N)
```

## Rule 7: Description Quality (Human-Readable)

**Applies to:** All `description` and `statement` fields that appear in the Decision Brief

```
CHECK: Description must NOT contain:
  - Underscores (snake_case leakage)
  - Backticks
  - Raw effect_id or assumption_key values

AUTO-FIX:
  "merchant_friction_persists increases 30%" → "Merchant friction increases 30%"
  (replace underscores with spaces, capitalize first letter)

FLAG BUT DON'T REJECT: descriptions shorter than 10 characters (may be too terse
for the brief but not structurally wrong)
```

## Rule 8: Second-Order Effect Completeness

**Applies to:** All first-order effects (order = 1)

```
CHECK: Every first-order effect must have `children` array with ≥ 1 entry.

IF MISSING: Log warning "Effect {effect_id} has no second-order children."
Do NOT reject — the analysis can proceed, but note in the brief that some
effects lack second-order analysis.
```

## Rule 9: Cross-Reference Integrity

**Applies to:** `effects-chains.json` (after synthesis)

```
CHECK 1: Every assumption key in any effect's `assumptions` array must exist
  in `all_assumptions`. If missing, create a stub.

CHECK 2: Every `parent_effect_id` in a 2nd-order effect must reference an
  existing 1st-order effect's `effect_id`. If orphaned, log warning.

CHECK 3: Every hypothesis referenced in effects must exist in hypotheses.json.
```

## Rule 10: Status Field Propagation

**Applies to:** All JSON output files

```
CHECK: Every JSON file must have a top-level "status" field.
  - "complete" = all expected content present
  - "partial" = some content missing (token limit, error, timeout)

PROPAGATION: If any persona file has status: partial, set effects-chains.json
status to partial. If effects-chains.json is partial, note in Decision Brief header.
```

## Rule 11: Journal Entry Schema

**Applies to:** Every append to `journal.jsonl` (Phase 8 and revise)

```
REQUIRED FIELDS: decision_id, decision_statement, timestamp, mode, iterations,
  converged (BOOLEAN only), recommendation, confidence (string: HIGH/MEDIUM/LOW only)

REQUIRED ARRAYS (of objects, NEVER strings):
  hypotheses: [{hypothesis_id, statement, status}]
  top_effects: [{effect_id, probability, council_agreement, description}]
  load_bearing_assumptions: [{key, sensitivity, fragility}]

NEVER:
  - "decision" instead of "decision_statement"
  - "slug" instead of "decision_id"
  - "date" instead of "timestamp"
  - converged as string ("primary_signals") — must be boolean
  - confidence as float (0.72) — must be string ("HIGH")
  - top_effects as array of strings — must be array of objects
  - Custom fields (walk_line_usd_m, output_style, runner_up) — use "notes" field

See references/journal-spec.md for the full strict schema.
```

## Rule 12: Assumption Library Schema

**Applies to:** Every append to `assumptions.jsonl`

```
FRAGILITY VOCABULARY: "SOLID", "SHAKEABLE", "FRAGILE" only
  NEVER: "HIGH"/"MEDIUM"/"LOW" (those are for sensitivity, not fragility)

SENSITIVITY VOCABULARY: "HIGH", "MEDIUM", "LOW" only

FIRST_SEEN FORMAT: ISO 8601 timestamp only
  NEVER: decision slugs, bare dates

CATEGORY: "market", "competition", "execution", "financial", "customer", "regulatory"

See references/assumption-library-spec.md for the full strict schema.
```

## Rule 13: Brief Structure Validity

**Applies to:** `DECISION-BRIEF.md` AFTER Phase 8 writes it, BEFORE the user sees it.

```
GATE: Run `scripts/validate-brief.py` with the canonical schema
  `references/brief-schema.json`. Full protocol in
  `references/phases/validate-brief.md`.

CHECKS:
  - All mandatory H2 sections present in the correct order
  - Mandatory subsections present under their parent (### Worst Cases etc.)
  - Required content patterns present (e.g. `**Action:**`, `**Confidence:**`)
  - Tables present where the schema requires them
  - No snake_case identifiers in prose (outside code, inline code, links)
  - Source tags valid: [G#], [D#], [U#], [C#:persona] recognized as valid tag classes
  - Cross-reference coverage: source JSON items traced via trailing
    `<!-- validator-refs: -->` block in the brief (legacy inline `<!-- ref:ID -->`
    also accepted for old briefs)
  - Recommendation never appears before position 12

SEVERITIES (from schema):
  - structural_section_missing       HARD_FAIL
  - section_out_of_order             HARD_FAIL
  - subsection_missing               HARD_FAIL
  - required_content_missing         HARD_FAIL
  - table_missing                    HARD_FAIL
  - snake_case_leak                  HARD_FAIL
  - cross_ref_coverage_below         HARD_FAIL
  - recommendation_before_pos_12     HARD_FAIL
  - table_columns_mismatch           WARN
  - raw_effect_id_in_prose           WARN
  - min_bullets_unmet                WARN

ON HARD_FAIL: re-prompt DECIDE once with the specific violations from
  validation-report.json. If retry also HARD_FAILs, prepend a
  VALIDATION_FAILED warning to the brief and continue.

ON WARN: continue. Append one-line validation footer to the brief.

ON SCRIPT ERROR (exit 3): log stderr, continue without validation. Never
  block a run on a broken validator.
```

The schema is canonical. If you change the brief template in `output-format.md`,
update `brief-schema.json` in the same commit, or the validator will reject briefs
that follow the new template.

## How to Apply These Rules

The orchestrator applies validation as follows:

0. **Before any other rule — Rule 0 first.** For every JSON file written by any phase,
   attempt to parse before any semantic check. If parse fails, run the auto-fix chain
   (trailing commas, comments, single quotes). If still unparseable, re-prompt once;
   if still unparseable, exclude the file and continue. No other rule can run on
   unparseable JSON.

1. **After persona subagents complete (Phase 3):** Apply Rule 0 to each
   `council/{persona}.json`. Then validate the parsed content against Rules 1-8.
   Auto-fix what's fixable. Log warnings. If a persona file fails critically
   (wrong structure entirely), exclude it from synthesis and note in peer review.

2. **After synthesis (effects-chains.json):** Apply Rule 0, then validate against
   Rules 1-10 (all rules). This is the most important checkpoint — effects-chains.json
   feeds all downstream phases.

3. **After convergence (judge-score.json):** Validate convergence parameters are
   non-negative integers.

4. **After Decision Brief (DECISION-BRIEF.md):** Run Rule 13 (the mechanical
   brief validator at `scripts/validate-brief.py` driven by
   `references/brief-schema.json`). This supersedes the ad-hoc snake_case scan —
   Rule 13 covers structure, content, cross-references, and prohibited patterns
   in one gate. Protocol details: `references/phases/validate-brief.md`.

## Error Handling

```
AUTO-FIXED: Log the fix silently. Continue.
WARNING: Log the issue. Continue. Note in brief if it affects confidence.
REJECT: Log the error. Re-prompt the agent once. If second attempt also fails,
  exclude the output and continue with remaining data. Never block the entire
  run for a single validation failure.
```
