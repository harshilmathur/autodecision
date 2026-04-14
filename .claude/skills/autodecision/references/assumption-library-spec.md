# Assumption Library Specification

## Purpose

Common assumptions recur across decisions. The assumption library stores them with
validation history — which decisions referenced them, whether they held or broke, and
how to test them. Over time this becomes an organizational knowledge asset.

## Storage

- Location: `~/.autodecision/assumptions.jsonl`
- Format: append-only JSONL
- Each line is an assumption entry or an update event

## Strict Schema Rules

**EVERY assumption entry MUST follow this exact schema.** Do NOT invent alternative
field names or vocabularies. Multiple vocabulary variants have been observed in the wild. To prevent inconsistency
and ensure the library works for cross-decision comparison, use ONLY the vocabularies below.

### Vocabulary (use ONLY these values)

| Field | Allowed Values | NEVER Use |
|-------|---------------|-----------|
| `sensitivity` | `"HIGH"`, `"MEDIUM"`, `"LOW"` | "CRITICAL", "MEDIUM-HIGH", numeric values |
| `fragility` | `"SOLID"`, `"SHAKEABLE"`, `"FRAGILE"` | "HIGH", "MEDIUM", "LOW" (those are for sensitivity, not fragility) |
| `first_seen` | ISO 8601 timestamp (`"2026-04-14T12:00:00Z"`) | Decision slugs, bare dates without time |
| `category` | `"market"`, `"competition"`, `"execution"`, `"financial"`, `"customer"`, `"regulatory"` | Free-form text |

**Sensitivity** = how much the conclusion changes if this assumption is wrong.
**Fragility** = how likely the assumption is to BE wrong.
These are different dimensions. An assumption can be HIGH sensitivity + SOLID (important but reliable) or LOW sensitivity + FRAGILE (likely wrong but doesn't matter).

## Assumption Entry Schema

```json
{
  "type": "assumption",
  "key": "price_sensitivity_moderate",
  "canonical_description": "Target market has moderate sensitivity to price changes",
  "category": "market",
  "first_seen": "2026-04-14T12:00:00Z",
  "decisions_referenced": [
    {
      "decision_id": "pricing-cut-20pct-full",
      "sensitivity": "HIGH",
      "fragility": "SHAKEABLE",
      "held": null
    }
  ],
  "times_referenced": 1,
  "times_held": 0,
  "times_broke": 0,
  "times_untested": 1,
  "test_method": "A/B test on 10-20% of traffic; analyze price elasticity of demand",
  "related_assumptions": ["market_has_unserved_demand", "market_is_value_driven"]
}
```

## Update Event Schema

When a decision outcome is recorded (via `/autodecision:review --outcome`):

```json
{
  "type": "validation",
  "key": "price_sensitivity_moderate",
  "decision_id": "pricing-cut-20pct-full",
  "timestamp": "2026-07-14T10:00:00Z",
  "result": "held",
  "evidence": "A/B test showed 28% acquisition increase with 20% price reduction, elasticity = -1.4",
  "notes": "Stronger than expected in SMB segment, weaker in enterprise"
}
```

## Categories

Assumptions are categorized for cross-decision matching:

| Category | Examples |
|----------|---------|
| `market` | price sensitivity, demand, saturation, growth rate |
| `competition` | competitor response, market dynamics, differentiation |
| `execution` | team capacity, timeline, technical feasibility |
| `financial` | unit economics, CAC, runway, margins |
| `customer` | churn, adoption, satisfaction, switching costs |
| `regulatory` | compliance, legal, contractual |

## Cross-Decision Matching

When a new decision generates assumptions in Phase 3 (SIMULATE), the system checks
the assumption library for matches:

1. **Exact key match:** Same `key` string (e.g., `price_sensitivity_moderate`)
2. **Semantic match:** Same `category` + high description similarity. The system should
   flag potential matches for the user to confirm.

When a match is found, surface it in the Decision Brief:

> "This assumption was used in 3 prior decisions. It held in 2, was invalidated in 1.
> Last test: 'A/B test showed elasticity = -1.4' (2026-07-14)."

## Staleness and Revalidation

Assumptions become stale over time. Rules:

- **Fresh:** Validated within last 6 months. Use with confidence.
- **Aging:** Validated 6-12 months ago. Use but flag as "may need revalidation."
- **Stale:** Validated >12 months ago OR never validated. Flag as "UNVALIDATED" and
  recommend testing.
- **Contradicted:** Validated as "broke" in recent decision. Flag with the contrary
  evidence. Do NOT remove — the contradiction is valuable data.

## Integration Points

### Phase 3 (SIMULATE)

Before personas generate effects, check the assumption library for relevant assumptions:

```
1. Read ~/.autodecision/assumptions.jsonl
2. For each assumption the personas are likely to use (based on decision category),
   check if a library entry exists
3. If found, include the validation history in the persona prompts:
   "NOTE: The assumption 'price_sensitivity_moderate' has been referenced in 3 prior
   decisions. It held 2/3 times. Last evidence: [evidence]. Consider this track record."
```

### Phase 8 (DECIDE)

After writing the Decision Brief:

```
1. Read the all_assumptions map from effects-chains.json
2. For each assumption:
   a. If it exists in the library: update times_referenced, add the decision_id
   b. If it doesn't exist: create a new entry
3. Append updates to ~/.autodecision/assumptions.jsonl
```

### /autodecision:review (with --outcome)

When the user records an outcome:

```
1. For each load-bearing assumption in the decision:
   a. Append a validation event to the library
   b. Update times_held / times_broke / times_untested
```
