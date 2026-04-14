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

## Field Definitions

| Field | Type | Set When | Description |
|-------|------|----------|-------------|
| `decision_id` | string | Phase 8 | The run slug |
| `decision_statement` | string | Phase 8 | Original decision question |
| `timestamp` | ISO 8601 | Phase 8 | When the brief was generated |
| `mode` | string | Phase 8 | "full" or "quick" |
| `iterations` | integer | Phase 8 | Number of iterations run |
| `converged` | boolean | Phase 8 | Whether convergence was reached |
| `recommendation` | string | Phase 8 | The action recommended |
| `confidence` | string | Phase 8 | HIGH / MEDIUM / LOW |
| `hypotheses` | array | Phase 8 | Summary of each hypothesis and its final status |
| `top_effects` | array | Phase 8 | Top 3-5 effects by council agreement and probability |
| `load_bearing_assumptions` | array | Phase 8 | Assumptions ranked HIGH sensitivity |
| `decision_boundaries` | array | Phase 8 | Specific thresholds that flip the conclusion |
| `run_path` | string | Phase 8 | Path to the full run directory |
| `outcome` | string | Review | What actually happened (user-provided) |
| `outcome_recorded_at` | ISO 8601 | Review | When the outcome was recorded |
| `outcome_notes` | string | Review | User's notes on what played out |
| `accuracy_score` | object | Review | Computed comparison of predictions vs actuals |

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
