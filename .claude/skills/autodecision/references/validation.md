# Output Validation Rules

This file defines validation rules applied by the orchestrator AFTER each phase
writes output. One file, one set of rules, applied everywhere. This ensures
consistent output across different models (Opus, Sonnet, Haiku) and systems.

The orchestrator reads this file once at run start and applies the relevant checks
after each phase completes.

## When to Validate

After EVERY phase that writes a JSON file. Read the file back, apply the rules
below, fix what can be fixed automatically, reject and re-prompt what can't.

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

## How to Apply These Rules

The orchestrator applies validation as follows:

1. **After persona subagents complete (Phase 3):** Validate each `council/{persona}.json`
   against Rules 1-8. Auto-fix what's fixable. Log warnings. If a persona file fails
   critically (wrong structure entirely), exclude it from synthesis and note in peer review.

2. **After synthesis (effects-chains.json):** Validate against Rules 1-10 (all rules).
   This is the most important checkpoint — effects-chains.json feeds all downstream phases.

3. **After convergence (judge-score.json):** Validate convergence parameters are
   non-negative integers.

4. **After Decision Brief (DECISION-BRIEF.md):** Scan for snake_case tokens
   (Rule 7 applied to the final markdown output). This is the last line of defense.

## Error Handling

```
AUTO-FIXED: Log the fix silently. Continue.
WARNING: Log the issue. Continue. Note in brief if it affects confidence.
REJECT: Log the error. Re-prompt the agent once. If second attempt also fails,
  exclude the output and continue with remaining data. Never block the entire
  run for a single validation failure.
```
