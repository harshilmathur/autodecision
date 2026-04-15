<!--
phase: 0
phase_name: SCOPE
runs_in:
  - full       (outer, runs once before the inner loop)
  - medium     (outer, runs once)
  - quick      (outer, runs once)
  - revise     (re-uses prior config, may patch via revision input)
reads:
  - user decision statement (from /autodecision invocation)
  - optional: --template flag (pricing | expansion | build-vs-buy | hiring)
  - if template: references/templates/{template}.md
writes:
  - ~/.autodecision/runs/{slug}/config.json
gates:
  - At least 2 sub-questions identified
  - Decision tilt set (default "balanced" if user did not specify)
-->

# Phase 0: SCOPE

## Purpose
Decompose the decision into sub-questions and constraints. This is the foundation
that all subsequent phases build on.

## Inputs
- User's decision statement (from the command invocation)

## Outputs
- `config.json` in the run directory

## Process

1. Parse the decision statement.
2. Decompose into 2-5 sub-questions. Each sub-question should be independently answerable.
   - If decomposition yields > 5 sub-questions, the decision is too broad. Ask the user to
     narrow it before proceeding.
   - If decomposition yields < 2, the decision may be too simple for the full loop.
     Suggest `/autodecision:quick` instead.
3. Identify explicit constraints (budget limits, timelines, non-negotiables).
4. Create the run directory and write `config.json`.

## Sub-Question Design

Good sub-questions are:
- **Independent:** answerable without solving the others first
- **Specific:** "How will existing customers react to a 20% price drop?" not "What about customers?"
- **Testable:** you could imagine searching for data that answers them

Bad sub-questions are:
- Circular: "Is this a good decision?" (that's the whole point)
- Too broad: "What will happen?" (decompose further)
- Too narrow: "Will revenue be $1.2M or $1.3M?" (false precision)

## Template Support

If the user specifies `--template pricing` (or another template name), read the
corresponding template file from `references/templates/{name}.md` and pre-populate
the sub-questions and constraints. The user can then modify them.

If no template is specified, decompose from scratch.

## Example Output

```json
{
  "status": "complete",
  "decision_statement": "Should we cut pricing by 20%?",
  "sub_questions": [
    "How will customer acquisition rate change with a 20% lower price?",
    "How will existing customers respond (churn, satisfaction, upsell)?",
    "How will competitors respond to our price change?",
    "What happens to unit economics and runway at the new price point?"
  ],
  "constraints": [
    "Must maintain positive unit economics within 12 months",
    "Cannot lose more than 5% of existing enterprise customers"
  ],
  "grounding": "PENDING",
  "template_used": null,
  "created_at": "2026-04-14T12:00:00Z"
}
```
