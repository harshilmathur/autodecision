# Decision Journal Specification

## Purpose

The decision journal tracks every decision run and its predicted outcomes.
Later, users can compare predictions vs actuals via `/autodecision:review`.
Over time this builds calibration data — which types of assumptions hold,
which fail, and how well the system's probability estimates match reality.

## Storage

- Location: `~/.autodecision/journal.jsonl`
- Format: append-only JSONL (one JSON object per line)
- Created automatically on first decision run

## Journal Entry Schema

Appended at the end of Phase 8 (DECIDE) for every decision run:

```json
{
  "decision_id": "pricing-cut-20pct-full",
  "decision_statement": "Should we cut pricing by 20%?",
  "timestamp": "2026-04-14T12:45:00Z",
  "mode": "full",
  "iterations": 2,
  "converged": true,
  "converged_at_iteration": 2,
  "grounding": "GROUNDED",
  "recommendation": "DO NOT cut pricing 20% across the board. Run controlled A/B promo experiment instead.",
  "confidence": "HIGH",
  "hypotheses": [
    {
      "hypothesis_id": "h1_volume_offset",
      "statement": "Blanket cut drives enough volume to offset revenue loss",
      "status": "eliminated"
    },
    {
      "hypothesis_id": "h3_value_market",
      "statement": "Market is value-driven, price cut barely moves acquisition",
      "status": "supported"
    }
  ],
  "top_effects": [
    {
      "effect_id": "irreversible_price_anchor",
      "probability": 0.825,
      "council_agreement": 5,
      "description": "Price cut creates one-way-door pricing expectation"
    }
  ],
  "load_bearing_assumptions": [
    {
      "key": "segments_are_separable",
      "sensitivity": "HIGH",
      "fragility": "FRAGILE"
    },
    {
      "key": "volume_offsets_revenue_loss",
      "sensitivity": "HIGH",
      "fragility": "FRAGILE"
    }
  ],
  "decision_boundaries": [
    "If segment leakage > 12%, recommendation flips to hold pricing",
    "If price elasticity < -0.5, no price cut is justified"
  ],
  "run_path": "~/.autodecision/runs/pricing-cut-20pct-full/",
  "outcome": null,
  "outcome_recorded_at": null,
  "outcome_notes": null,
  "accuracy_score": null
}
```

## Field Definitions (STRICT — all required unless marked optional)

EVERY journal entry MUST use exactly these field names and types. Do NOT invent
alternative field names (no `decision` instead of `decision_statement`, no `slug`
instead of `decision_id`, no `date` instead of `timestamp`). Do NOT add custom
fields outside the schema (no `walk_line_usd_m`, no `output_style`, no `runner_up`).
If you need decision-specific data, put it in `notes` (string, optional).

| Field | Type | Required | Allowed Values / Format | Description |
|-------|------|----------|------------------------|-------------|
| `decision_id` | string | YES | lowercase-kebab-case slug | The run directory name |
| `decision_statement` | string | YES | free text | The original decision question |
| `timestamp` | string | YES | ISO 8601 (`2026-04-14T12:45:00Z`) | When the brief was generated |
| `mode` | string | YES | `"full"`, `"quick"`, `"medium"`, `"challenge"`, `"revision"` | Which command was used |
| `iterations` | integer | YES | 0-5 | Number of iterations run (0 for quick/challenge) |
| `converged` | boolean | YES | `true` or `false` ONLY | Never strings like "primary_signals" |
| `converged_at_iteration` | integer or null | YES | 1-5 or null | Which iteration converged, null if not |
| `grounding` | string | YES | `"GROUNDED"` or `"UNGROUNDED"` | Whether Phase 1 found data |
| `tilt` | string or null | YES | `"maximize_enterprise_value"`, `"moat"`, `"capital_efficiency"`, `"time_to_market"`, `"risk_minimization"`, `null` | User's strategic tilt |
| `recommendation` | string | YES | free text, one sentence | The action recommended |
| `confidence` | string | YES | `"HIGH"`, `"MEDIUM"`, `"LOW"` ONLY | Never `"HIGH (0.72)"`, never a float |
| `hypotheses` | array of objects | YES | see sub-schema below | NEVER an array of strings |
| `top_effects` | array of objects | YES | see sub-schema below | NEVER an array of strings |
| `load_bearing_assumptions` | array of objects | YES | see sub-schema below | NEVER an array of strings |
| `decision_boundaries` | array of strings | YES | human-readable sentences | Specific thresholds |
| `run_path` | string | YES | `"~/.autodecision/runs/{slug}/"` | Path to run directory |
| `notes` | string or null | optional | free text | Any decision-specific data that doesn't fit above |
| `outcome` | string or null | YES | null until recorded | What actually happened |
| `outcome_recorded_at` | string or null | YES | ISO 8601 or null | When outcome was recorded |
| `outcome_notes` | string or null | YES | null until recorded | User's notes |
| `accuracy_score` | object or null | YES | null until recorded | Prediction vs reality comparison |

### Sub-schema: hypothesis object

```json
{"hypothesis_id": "h1_volume_offset", "statement": "Price cut drives volume", "status": "eliminated"}
```

| Field | Type | Allowed Values |
|-------|------|---------------|
| `hypothesis_id` | string | `h{N}_{descriptor}` format |
| `statement` | string | human-readable, one sentence |
| `status` | string | `"supported"`, `"weakened"`, `"eliminated"`, `"conditional"` |

### Sub-schema: top_effect object

```json
{"effect_id": "irreversible_price_anchor", "probability": 0.825, "council_agreement": 5, "description": "Price cut creates one-way-door pricing expectation"}
```

| Field | Type | Allowed Values |
|-------|------|---------------|
| `effect_id` | string | snake_case (internal, not shown in brief) |
| `probability` | float | 0.05-0.95, in 0.05 increments |
| `council_agreement` | integer or null | 1-5, null for quick/challenge mode |
| `description` | string | human-readable, NO snake_case |

### Sub-schema: assumption object

```json
{"key": "segments_are_separable", "sensitivity": "HIGH", "fragility": "FRAGILE"}
```

| Field | Type | Allowed Values |
|-------|------|---------------|
| `key` | string | snake_case |
| `sensitivity` | string | `"HIGH"`, `"MEDIUM"`, `"LOW"` |
| `fragility` | string | `"SOLID"`, `"SHAKEABLE"`, `"FRAGILE"` |

### Revision entry sub-schema

Revision entries use the SAME top-level schema plus these additional fields:

| Field | Type | Description |
|-------|------|-------------|
| `original_decision_id` | string | The slug of the original run being revised |
| `revision_input` | string | The user's natural language revision input |
| `changes_applied` | array of strings | What was changed |
| `recommendation_changed` | boolean | Did the revision flip the recommendation? |

## Outcome Recording

When the user runs `/autodecision:review {slug} --outcome "..."`:

1. Find the journal entry by `decision_id`
2. Set `outcome`, `outcome_recorded_at`, `outcome_notes`
3. Compute `accuracy_score`:

```json
{
  "effects_predicted": 7,
  "effects_correct": 4,
  "effects_partially_correct": 2,
  "effects_wrong": 1,
  "assumption_accuracy": {
    "held": ["segments_are_separable", "enterprise_is_value_driven"],
    "broke": ["volume_offsets_revenue_loss"],
    "untested": ["competitor_is_price_responsive"]
  },
  "recommendation_followed": true,
  "recommendation_correct": true
}
```

4. Rewrite the JSONL line in place (read all, modify, write all) or append
   a new line with `"type": "outcome"` referencing the decision_id.

## Integration with Phase 8

At the end of Phase 8 (DECIDE), after writing `DECISION-BRIEF.md`:

```
1. Construct the journal entry from the brief's data
2. Append to ~/.autodecision/journal.jsonl
3. Print to user: "Decision logged to journal. Run `/autodecision:review` later to compare predictions vs reality."
```
