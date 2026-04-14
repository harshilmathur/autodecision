# Phase 0.5: ELICIT

## Purpose

Before the loop runs, review the analysis setup with the user. This is the single
biggest quality improvement: getting domain-specific knowledge and user preferences
BEFORE the system starts simulating. Every minute spent here saves 10 minutes of
irrelevant simulation.

## Inputs
- `config.json` (from Phase 0: decision, sub-questions, constraints)
- `ground-data.md` (from Phase 1: web search results)

## Outputs
- `user-inputs.md` in the run directory
- Potentially updated `config.json` (if user modifies sub-questions or constraints)

## Process

Present three review blocks to the user via AskUserQuestion. Each block is skippable.

### Block 1: Review Assumptions and Data

Present the key findings from ground-data.md and the sub-questions from config.json:

> "Before I start the analysis, here's what I'm working with. Any corrections or additions?"
>
> **Decision:** {decision_statement}
>
> **Sub-questions I'll analyze:**
> 1. {sub-question 1}
> 2. {sub-question 2}
> ...
>
> **Key data I found (Phase 1 grounding):**
> - {top 3-5 data points from ground-data.md}
>
> **Does this look right? Anything I'm missing or getting wrong?**
>
> Options:
> A) Looks good, proceed
> B) I have corrections / additional data (provide below)
> C) Skip — just run the analysis

If user provides corrections or data:
- Record in `user-inputs.md`
- Update `config.json` if sub-questions change
- Tag user-provided data as "(user-provided)" throughout the analysis

### Block 2: Review Personas

Present the 5 default personas and ask if the user wants to modify:

> **Council personas for this decision:**
>
> 1. **Growth Optimist** — looks for upside, market opportunity, creative alternatives
> 2. **Risk Pessimist** — looks for downside, failure modes, hidden costs
> 3. **Competitor Strategist** — thinks like the competition
> 4. **Regulator/Constraint** — sees legal, regulatory, structural constraints
> 5. **Customer Advocate** — thinks like the end user
>
> These work well for most business decisions. You can:
> - **Add a persona** (e.g., "Investor" for fundraising decisions, "Engineer" for technical decisions)
> - **Remove a persona** (e.g., Regulator may be irrelevant for some decisions)
> - **Modify a persona** (e.g., change Competitor to a specific competitor name)
>
> Options:
> A) Default 5 personas — proceed
> B) I want to customize (specify below)
> C) Skip

If user customizes:
- Record custom persona definitions in `user-inputs.md`
- Update persona prompts accordingly for this run
- Custom personas follow the same structure: optimization objective, blind spot,
  contrarian question, no-hedging rule

### Block 3: Additional Domain Knowledge

Ask targeted questions based on the decision type and data gaps:

> **A few questions that would sharpen the analysis (answer any, skip the rest):**
>
> 1. {question derived from the biggest data gap in ground-data.md}
>    Example: "What's your current churn rate?" / "Who is your primary competitor?"
> 2. {question about internal context the system can't search for}
>    Example: "What's your current runway?" / "What % of revenue comes from enterprise?"
> 3. {question about the user's risk tolerance or decision framework}
>    Example: "Are you optimizing for growth or profitability?" / "Is this reversible if it fails?"
>
> Options:
> A) Here are my answers: {free text}
> B) Skip — work with what you have

Generate 3-5 questions based on:
- Missing data flagged in `ground-data.md`
- Constraints in `config.json` that need quantification
- Decision template guidance (if a template was used)
- Common data gaps for this decision type

If user provides answers:
- Record in `user-inputs.md`
- Feed into persona prompts as "USER-PROVIDED CONTEXT: {data}"
- Tag in the Decision Brief as "(user-provided)"

## Output: user-inputs.md

```markdown
# User Inputs: {decision_statement}

## Assumptions Review
- Status: {REVIEWED / SKIPPED}
- Corrections: {any corrections to sub-questions or ground data}
- Additional data: {any data the user provided}

## Persona Configuration
- Status: {DEFAULT / CUSTOMIZED / SKIPPED}
- Changes: {any persona additions, removals, or modifications}
- Custom personas: {definitions if any}

## Domain Knowledge
- Status: {PROVIDED / SKIPPED}
- Answers:
  1. {question}: {answer}
  2. {question}: {answer}
  3. {question}: {answer}
```

## Skip Behavior

If the user skips ALL three blocks (or the command includes `--skip-elicit`):
- Write `user-inputs.md` with all statuses as "SKIPPED"
- Proceed immediately to Phase 2

The ELICIT phase should take < 2 minutes if the user engages, 0 seconds if skipped.
It should NEVER feel like a barrier to running the analysis.

## Integration with Personas

When user-inputs.md contains domain knowledge, EVERY persona subagent prompt
should include:

```
USER-PROVIDED CONTEXT (treat as high-confidence data, more reliable than web search):
- {data point 1}
- {data point 2}
- {data point 3}
```

This ensures user knowledge flows through the entire analysis, not just the grounding.
