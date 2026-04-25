---
name: autodecision:deck
description: Render a Decision Brief as a McKinsey-styled PPTX deck (~16 slides)
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Skill
  - AskUserQuestion
---

# /autodecision:deck

Turn a Decision Brief into a McKinsey-styled PowerPoint deck. Reads
`~/.autodecision/runs/{slug}/DECISION-BRIEF.md`, synthesizes action-title
claims, and emits `DECK.pptx` (~16 slides) into the same run directory.

The deck reads as a coherent narrative: pyramid principle (recommendation
up front), then exploration of hypotheses, council findings with
adversarial pressure, then path forward. Every slide title is a complete
sentence making a claim — the slide content is the evidence.

## Invocation

```
/autodecision:deck                    # interactive — pick a run
/autodecision:deck {slug}             # render that run's brief into a deck
/autodecision:deck {slug} --open      # render and open in default app
```

## Examples

```
/autodecision:deck adobe-deprecate-photoshop-ui
/autodecision:deck pricing-cut-20pct-full --open
```

## Output

Writes two files into the run directory:

- `~/.autodecision/runs/{slug}/deck-spec.json` — the structured spec used by
  the renderer (re-runnable, edit-then-rerender if you want to tweak)
- `~/.autodecision/runs/{slug}/DECK.pptx` — the rendered deck

## Constraints

- **Full-mode briefs only.** Quick-mode briefs lack the council disagreement,
  adversarial scenarios, and sensitivity data the radar / 2×2 / tornado
  slides depend on. If invoked on a quick run, prompt the user to either
  run the full loop first or accept a reduced 8-slide version.
- **Brief schema v1.1+.** The orchestrator fails fast if mandatory headers
  are missing (per `brief-schema.json`). Fix the brief first, then re-run.
- **Never modifies the source brief.** Read-only against
  `DECISION-BRIEF.md`.

## Execution

Read `references/phases/deck.md` for the full protocol — section parsing,
action-title synthesis rules, position synthesis for the 2×2 and radar
exhibits, deck-spec.json schema, and the renderer invocation.
