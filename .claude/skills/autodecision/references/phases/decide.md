# Phase 8: DECIDE

## Purpose
Final synthesis. Produce the Decision Brief — the primary output of the system.

## Inputs
- `config.json`, `ground-data.md`
- All iteration outputs (read only the LATEST iteration's files + `convergence-log.json`)
- `convergence-log.json` (full iteration history)

## Outputs
- `DECISION-BRIEF.md`

## CRITICAL: Human-Readable Output

Before writing ANY part of the brief, internalize this rule:

**The brief is a strategy memo for decision-makers. NEVER show internal identifiers.**

When you read `effect_id: "cci_phase2_review"` with `description: "CCI triggers
Phase-2 review"` from effects-chains.json, the brief says "CCI triggers Phase-2
review (P=0.80)" — NEVER "`cci_phase2_review` (0.80)".

Same for assumptions: `bank_partner_willing` in JSON becomes "At least one major
bank willing to partner" in the brief. Always use the `description` field, never
the `key` field.

Same for hypotheses: `h7_acquire_and_carve_jv` becomes "H7: Acquire + carve out
cross-border into bank JV".

If you catch yourself writing snake_case or backtick-wrapped identifiers in the
brief text, stop and rewrite. The reader should never see an underscore.

## Process

### Step 1: Read Final State

Read the latest iteration's:
- `effects-chains.json` (the converged or final effects map)
- `sensitivity.json` (decision boundaries and assumption rankings)
- `adversary.json` (worst cases and black swans)
- `peer-review.json` (council agreement and rankings)
- `convergence-log.json` (convergence history)

### Step 2: Classify Insights

**Stable insights:** Effects present across all iterations with probability shift < 0.1
and `council_agreement` >= 3. These survived adversarial pressure.

**Fragile insights:** Effects with HIGH sensitivity assumptions, wide probability ranges
(> 0.3), or `council_agreement` < 3. These depend on assumptions that could be wrong.

### Step 3: Generate Recommendation

Apply expected value reasoning across the hypothesis space:
- For each hypothesis, compute the expected net impact by weighting effects by probability
- Factor in worst-case scenarios from the adversary phase
- Identify the action with the best expected outcome ACROSS hypotheses
- Note which assumptions the recommendation depends on

### Step 4: Write Decision Brief

Write `DECISION-BRIEF.md` using the template from `references/output-format.md`.

### Step 5: Persist to Journal and Assumption Library

**This step is MANDATORY. The journal and assumption library are the compounding
knowledge assets. Without them, /autodecision:review and /autodecision:export
have nothing to work with.**

**5a. Append to journal.jsonl:**

```bash
# Create file if it doesn't exist
touch ~/.autodecision/journal.jsonl
```

Construct a journal entry JSON object (see `references/journal-spec.md` for full schema):
- `decision_id`: the run slug
- `decision_statement`: from config.json
- `timestamp`: current ISO 8601
- `mode`: "full" or "quick"
- `iterations`: number completed
- `converged`: boolean
- `recommendation`: one-line action from the brief
- `confidence`: HIGH/MEDIUM/LOW
- `hypotheses`: array of {hypothesis_id, statement, status}
- `top_effects`: top 3-5 effects by council_agreement and probability
- `load_bearing_assumptions`: assumptions with sensitivity HIGH
- `decision_boundaries`: from sensitivity analysis
- `tilt`: from config.json
- `outcome`: null (set later via /autodecision:review)

Append this as ONE line to `~/.autodecision/journal.jsonl`.

**5b. Update assumption library:**

```bash
touch ~/.autodecision/assumptions.jsonl
```

For each assumption in the final `effects-chains.json > all_assumptions`:
- Read `~/.autodecision/assumptions.jsonl`
- If assumption key already exists: append a reference entry updating `times_referenced`
  and adding this `decision_id`
- If assumption key is new: append a new assumption entry with `first_seen`, initial
  `times_referenced: 1`, and this decision's sensitivity/fragility ratings

**5c. Print to user:**

Print the full Decision Brief. Then print:
"Decision logged to journal. Run `/autodecision:review` to compare predictions vs reality later."

### Step 6: Print Brief to User

After persisting, print the full Decision Brief to the conversation so the
user can see it immediately.

## Handling Incomplete Data

If phases are missing (status: partial or file missing):
- Note which phases are incomplete in the Brief header
- Reduce confidence rating accordingly
- Proceed with available data — an incomplete analysis is better than no analysis

## Convergence Status in Brief

- **Converged at iteration N:** "Insights stabilized after N iterations of adversarial pressure."
- **NOT REACHED after 3 iterations:** "Convergence not reached. This decision has genuine
  unresolvable uncertainty. The effects below represent the best available analysis but
  may shift with additional iteration. Delta values: [effects_delta], [assumption_stability],
  [ranking_flips], [contradictions]."

## Quick Mode Variant

For `/autodecision:quick`, Phase 8 produces a lighter brief:
- No convergence data (single pass)
- No council agreement (no council)
- No sensitivity analysis
- No adversary scenarios
- Probabilities are point estimates only (no ranges)
- Still includes: hypotheses, effects, assumptions, recommendation
