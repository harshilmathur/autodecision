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

## ⚠️ HARD RULE — invoke the renderer, do not write python-pptx inline

**This command is NOT "produce a PPTX from this brief, however you like."**
**It is "produce `deck-spec.json`, then run `scripts/render-deck.py` to
render it into `DECK.pptx`."**

Building the PPTX inline with `python-pptx`, `Bash` heredocs, or any
other "I'll just create a presentation directly" approach is FORBIDDEN.
The renderer ships specific visual elements that the inline path will
never reproduce:

- The orbital council mark on the cover (5 persona dots → navy synthesis
  centre with 2nd-order effect ring)
- The small brand mark in every body-slide footer
- Georgia serif action titles + the McKinsey navy/blue palette
- Status pills in the hypotheses table (coloured discs + adaptive font)
- The 2×2 strategic positioning matrix (matplotlib bubble chart)
- The horizontal effects bar chart (council-agreement coloured bars +
  black uncertainty range brackets)
- The 5-persona radar chart (polar plot)
- The sensitivity tornado (HIGH/MEDIUM/LOW colour-tier bars)
- Five PowerPoint compatibility hooks that strip a printerSettings
  binary, normalise slide size, populate the root group transform, add
  trailing endParaRPr, and force int EMU values

Without the renderer you get plain text-on-rectangles slides, no
charts, no cover graphic, and a PowerPoint repair prompt on open.

If `scripts/render-deck.py` is NOT available in the skill's directory,
**STOP and tell the user the plugin install is broken** — do not
improvise. The renderer is the deliverable.

The protocol below names exactly two phases: synthesise a
`deck-spec.json` from the brief, then invoke the renderer with that
spec. Read `references/phases/deck.md` and follow it literally.

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
