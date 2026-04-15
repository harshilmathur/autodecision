# Progress Templates (TodoWrite)

The orchestrator MUST surface a live progress tracker via `TodoWrite` so the user sees where the loop stands. Update at EVERY phase transition. Only ONE item should be `in_progress` at a time.

Pick the template that matches the active mode. Initialize at the start of the run.

## Full Loop Template (`/autodecision`, default 2 iterations)

```
Phase 0: Scope — decompose decision              [pending]
Phase 1: Ground — web search for data             [pending]
Phase 1.5: Elicit — review with user              [pending]
Phase 2: Hypothesize — generate competing paths   [pending]
Phase 3: Simulate — 5 persona council (parallel)  [pending]
Phase 3b: Synthesis — merge persona outputs       [pending]
Phase 4+5: Critique + Adversary (parallel)        [pending]
Phase 6: Sensitivity — find decision boundaries   [pending]
Phase 7: Converge — judge stability               [pending]
Iteration 2: Refine — light-mode re-simulation    [pending]
Phase 8: Decide — generate Decision Brief         [pending]
Persist — journal + assumption library            [pending]
Phase 8.5: Validate — mechanical brief check      [pending]
```

For deep mode (`--iterations 3-5`), append `Iteration 3..N: Refine` rows as needed before Phase 8.

## Medium Mode Template (`--iterations 1`)

```
Phase 0: Scope — decompose decision              [pending]
Phase 1: Ground — web search for data             [pending]
Phase 1.5: Elicit — review with user              [pending]
Phase 2: Hypothesize — generate competing paths   [pending]
Phase 3: Simulate — 5 persona council (parallel)  [pending]
Phase 3b: Synthesis — merge persona outputs       [pending]
Phase 4+5: Critique + Adversary (parallel)        [pending]
Phase 6: Sensitivity — find decision boundaries   [pending]
Phase 8: Decide — generate Decision Brief         [pending]
Persist — journal + assumption library            [pending]
Phase 8.5: Validate — mechanical brief check      [pending]
```

(No Phase 7 — medium mode skips convergence.)

## Quick Mode Template (`/autodecision:quick`)

```
Phase 0: Scope — decompose decision              [pending]
Phase 1: Ground — web search for data             [pending]
Phase 3: Simulate — single-pass analysis          [pending]
Phase 8: Decide — generate Quick Brief            [pending]
Phase 8.5: Validate — mechanical brief check      [pending]
```

## Revise Template (`/autodecision:revise`)

```
Read prior run + revision input                   [pending]
Re-simulate with changed assumptions              [pending]
Re-run sensitivity with new boundaries            [pending]
Phase 8: Decide — write revised brief             [pending]
Persist — journal + assumption library            [pending]
Phase 8.5: Validate — mechanical brief check      [pending]
```

## Challenge Template (`/autodecision:challenge`)

```
Parse stated action as single hypothesis          [pending]
Phase 1: Ground — narrow search for action        [pending]
Phase 5: Adversary — worst cases + black swans    [pending]
Phase 6: Sensitivity — decision boundaries        [pending]
Write Challenge Brief                             [pending]
```

## Rules

- Mark `in_progress` when you START a phase, `completed` when you FINISH it.
- One `in_progress` at a time, never zero, never two.
- Do NOT collapse phases into a single bullet — the user is reading this to know exactly where the analysis stands.
- If a phase fails or partially completes, mark it `completed` but note the partial in the brief header. The progress tracker is for visibility, not for blocking.
