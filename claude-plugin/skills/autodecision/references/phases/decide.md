# Phase 8: DECIDE

## Purpose
Make the possibility map legible. The brief is a decision map: what the exploration surfaced, where the council diverged, what survived adversarial pressure, what didn't. A recommendation appears at the end as one synthesis of the map, not as the product.

The possibility map IS the output. The decision is a downstream convenience for readers who need a single action. Do not compress the map to make the recommendation faster to find — the map is why we spent the compute.

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

Same for hypotheses: `h3_build_in_house` becomes "H3: Build the capability in-house".

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

### Step 3: Synthesize Findings

The goal of Phase 8 is to make the exploration legible. That means two passes:

**Pass 1 — Map the possibility space.** For each major bucket the loop produced (hypotheses, effects by agreement tier, council dynamics, stable and fragile insights, adversarial scenarios, assumptions), write the section that shows what the exploration found in its own terms. Do NOT pre-summarize toward a recommendation. Do NOT drop a section because "the reader just wants the answer." The map IS the answer.

**Pass 2 — Synthesize a recommendation.** After the map is written, apply expected value reasoning across the hypothesis space:
- For each hypothesis, compute the expected net impact by weighting effects by probability
- Factor in worst-case scenarios and black swans from the adversary phase
- Identify the action with the best expected outcome ACROSS hypotheses
- Note which assumptions the recommendation depends on

The recommendation goes at the end of the brief (section 12), not the top. The Executive Summary at the top gives readers a 30-second preview of the map with the recommendation called out, but it is NOT a substitute for the full Recommendation block at the end.

### Step 4: Write Decision Brief

Write `DECISION-BRIEF.md` using the template from `references/output-format.md`.

**MANDATORY SECTIONS (never skip, never rename, in this order):**

1. **Executive Summary** — 6-line bullet box. Decision, Recommendation (called out), Confidence, Hypotheses explored, Deepest disagreement, Dominant risk, Load-bearing assumption. NOT a standalone memo — a preview of the map with the recommendation visible. Literal header "## Executive Summary" — never "Bottom Line", "Headline", or "Summary".
2. **Data Foundation**
3. **Hypotheses Explored** (table format)
4. **Effects Map** (High-Confidence / Specialist / Exploratory subsections)
5. **Council Dynamics** (who thought what, where they diverged — the diversity signal, not a footnote)
6. **Minority-View Winners** (optional — include only if a single-persona insight became the recommendation)
7. **Stable Insights** (what survived adversarial pressure across iterations)
8. **Fragile Insights** (with decision boundaries)
9. **Adversarial Scenarios** (Worst Cases + Black Swans + Irrational Actors subsections — placed AFTER Stable/Fragile so readers know what held up before seeing what attacks it)
10. **Key Assumptions** (ranked by sensitivity)
11. **Convergence Log** (omit for medium mode, omit for quick mode)
12. **Recommendation** (the full 7-field synthesis block — Action, Confidence, Confidence reasoning, Depends on, Monitor, Pre-mortem, Review trigger)
13. **Appendix A: Decision Timeline**

The order signals what matters. Sections 2-11 are the possibility map. Section 12 is one synthesis of that map. The Executive Summary at section 1 lets decision-makers skim, but the bulk of the brief is exploration.

**Common failure modes to avoid:**
- Renaming "Executive Summary" to "Bottom Line", "Headline", or "Summary" — use the literal header.
- Renaming "Hypotheses Explored" to "Hypothesis Ranking" or similar — use the literal header.
- Moving Recommendation back to the top — it belongs at section 12.
- Dropping Black Swans or Irrational Actors from Adversarial Scenarios when the adversary phase produced them — never drop a subsection that has source data.
- Compressing Council Dynamics to one line — this is one of the main outputs, not a footnote. At minimum 5 bullets.
- Conflating Stable Insights and the Recommendation — Stable Insights are findings about the map, Recommendation is an action synthesized from those findings.
- Using `effect_id` or `assumption_key` in human-readable text — always use the description field, replace underscores with spaces, capitalize the first letter.

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

### Step 5b: Revision Chain Header

Before finalizing the brief, check if revisions of this decision exist:

```bash
ls -d ~/.autodecision/runs/{slug}-revise-* 2>/dev/null
```

If revisions exist, add a revision chain line below the brief header metadata:

```
**Revision chain:** Original → [Revise 1: {change}]({path}) → [Revise 2: {change}]({path})
```

Read each revision's `config.json` or `user-inputs.md` to extract the change description.
If this IS a revision run, also add:
```
**This is a revision of:** [{original slug}]({original path}) | **Change:** "{revision input}"
```

### Step 6: Print Brief to User

After persisting, print the full Decision Brief to the conversation. Then print:
"Decision logged to journal. Run `/autodecision:review` to compare predictions vs reality later."

### Step 7: Offer Export

After printing, offer to export to the current working directory:

> "Export brief to current directory?"
> Options: A) Export full brief  B) Skip

If A:
```bash
cp ~/.autodecision/runs/{slug}/DECISION-BRIEF.md ./{slug}-DECISION-BRIEF.md
```
Print: "Exported to ./{slug}-DECISION-BRIEF.md"

## Handling Incomplete Data

If phases are missing (status: partial or file missing):
- Note which phases are incomplete in the Brief header
- Reduce confidence rating accordingly
- Proceed with available data — an incomplete analysis is better than no analysis

## Convergence Status in Brief

- **Converged at iteration N:** "Insights stabilized after N iterations of adversarial pressure."
- **NOT REACHED after max iterations:** "Convergence not reached. This decision has genuine
  unresolvable uncertainty. The effects below represent the best available analysis but
  may shift with additional iteration. Delta values: [effects_delta], [assumption_stability],
  [ranking_flips], [contradictions]."

## Medium Mode (--iterations 1)

Medium mode produces the SAME brief structure as full mode. Do NOT improvise an
alternative layout. Use the identical template from `references/output-format.md`.
The only differences:
- Header shows: `Iterations: 1 | Converged: N/A (medium mode)`
- Omit the Convergence Log section entirely (no convergence data exists)
- Council Dynamics section still includes persona rankings and key disagreements

Do NOT lead with recommendation, do NOT use "Why Not X" sections, do NOT drop
Data Foundation or Hypotheses table. One template, one structure, regardless of
iteration count. The reader should not need to know how many iterations ran to
understand the brief.

## Quick Mode Variant

For `/autodecision:quick`, Phase 8 produces a lighter brief:
- No convergence data (single pass)
- No council agreement (no council)
- No sensitivity analysis
- No adversary scenarios
- Probabilities are point estimates only (no ranges)
- Still includes: hypotheses, effects, assumptions, recommendation
