<!--
phase: 4
phase_name: CRITIQUE (team-mode variant)
runs_in:
  - full.team.iteration-1    (rotating peer reviews + bounded debate)
  - full.team.iteration-2+   (only if convergence failed; else carries forward from iter-1)
  - medium.team.iteration-1  (same as full.team.iter-1)
  - NOT in non-team modes    (use phases/critique.md instead)
  - NOT in quick mode
reads:
  - ~/.autodecision/runs/{slug}/iteration-{N}/council/*.json (all 5)
  - ~/.autodecision/runs/{slug}/iteration-{N}/effects-chains.json
writes:
  - ~/.autodecision/runs/{slug}/iteration-{N}/peer-review/{reviewer}.json × 5 (per-reviewer files)
  - ~/.autodecision/runs/{slug}/iteration-{N}/peer-review.json (synthesized from the 5 — same path as non-team)
  - ~/.autodecision/runs/{slug}/iteration-{N}/critique.json (consolidated flaws — same path as non-team)
  - ~/.autodecision/runs/{slug}/iteration-{N}/debate-transcript.jsonl (append-only log of cross-teammate messages)
gates:
  - bounded_debate: max 2 message exchanges per reviewer-author pair
  - total_debate_time: max 10 minutes wall-clock
-->

# Phase 4: CRITIQUE (team mode)

## Purpose

Replace the non-team "single anonymous reviewer reads all 5 JSONs" protocol with **rotating peer review plus bounded cross-teammate debate**. Each teammate reviews exactly one other teammate's analysis and can challenge specific effects via direct SendMessage. The author pushes back or concedes. After a bounded exchange, both emit structured JSON.

The downstream `peer-review.json` and `critique.json` contract is **identical** to the non-team variant. Phase 7 CONVERGE reads the same files and computes the same Judge metrics. Anonymization is dropped in team mode (teammates know each other's identities); ranking-flip metric reliability is already documented as a warning-only signal in `converge.md`, so this does not break the Judge.

## Inputs

- `iteration-{N}/council/*.json` — the 5 persona outputs from Phase 3
- `iteration-{N}/effects-chains.json` — synthesized effects map

## Outputs

- `iteration-{N}/peer-review/{reviewer}.json` (5 new files — one per reviewer)
- `iteration-{N}/peer-review.json` (synthesized; same schema as non-team)
- `iteration-{N}/critique.json` (same schema as non-team)
- `iteration-{N}/debate-transcript.jsonl` (new; team mode only, for audit)

## Process

### Step 1: Lead assigns rotating review pairs

Rotate reviewers so no one reviews themselves and coverage is uniform. Standard rotation:

| Reviewer | Reviews |
|----------|---------|
| optimist   | pessimist  |
| pessimist  | competitor |
| competitor | regulator  |
| regulator  | customer   |
| customer   | optimist   |

Lead posts 5 tasks to the shared task list, one per reviewer, with the task description:

> **CRITIQUE task.** Read `iteration-{N}/council/{author-short-tag}.json` and `iteration-{N}/effects-chains.json`. Critique the author's analysis on four dimensions: groundedness, specificity, diversity, blind spots. Rate 1–5 on each. Rank all 5 analyses from strongest to weakest (you've seen one in depth; form opinions on the others from effects-chains.json).
>
> Identify up to 3 specific flaws or missing variables in the author's analysis. For each flaw, message the author directly via SendMessage with a concrete challenge (*"Your effect `acq_increase` at P=0.75 assumes price sensitivity is 'moderate'. Ground data G3 shows sensitivity is 'high' for mid-market. Why not lower P to 0.55?"*).
>
> The author may reply with a correction or a defense. You get up to 2 exchanges per flaw. After that, write your final review to `iteration-{N}/peer-review/{your-short-tag}.json` per the schema below.

### Step 2: Bounded debate

**Hard cap: 2 message exchanges per reviewer-author pair.** After 2 rounds, both parties must finalize their positions. If the reviewer remains unconvinced, the flaw is recorded as `"resolved": false, "author_position": "..."`.

**Hard cap: 10 minutes wall-clock for the entire phase.** If the deadline approaches, the lead broadcasts: *"10-minute debate window expires in 60 seconds. Finalize your reviews."* Remaining unresolved flaws are recorded with `"resolved": "timeout"`.

Every message exchange is appended to `debate-transcript.jsonl`:

```jsonl
{"timestamp": "...", "from": "optimist", "to": "pessimist", "flaw_ref": "F1", "content": "..."}
{"timestamp": "...", "from": "pessimist", "to": "optimist", "flaw_ref": "F1", "content": "..."}
```

The transcript is audit-only. It does not feed into `critique.json` or the brief — only the resolved/unresolved flaws do.

### Step 3: Reviewers emit per-reviewer JSON

Each reviewer writes `iteration-{N}/peer-review/{reviewer}.json`:

```json
{
  "status": "complete",
  "reviewer": "optimist",
  "reviewed": "pessimist",
  "ratings": {
    "groundedness": 4,
    "specificity": 3,
    "diversity": 4,
    "blind_spots": 2
  },
  "rankings": [
    {"persona": "regulator",  "rank": 1},
    {"persona": "competitor", "rank": 2},
    {"persona": "pessimist",  "rank": 3},
    {"persona": "customer",   "rank": 4},
    {"persona": "optimist",   "rank": 5}
  ],
  "flaws": [
    {
      "flaw_id": "F1",
      "effect_ref": "acq_increase",
      "description": "Probability too high given ground data G3",
      "resolved": true,
      "resolution": "author agreed, revised P to 0.55"
    },
    {
      "flaw_id": "F2",
      "effect_ref": "price_war_escalation",
      "description": "Missing competitor scenario where Acme matches and adds loyalty program",
      "resolved": false,
      "author_position": "out of scope for this hypothesis"
    }
  ]
}
```

### Step 4: Lead synthesizes into canonical files

Inline, the orchestrator reads all 5 `peer-review/{reviewer}.json` files and synthesizes:

**`peer-review.json`** (schema matches non-team, minus the anonymization mapping):

```json
{
  "status": "complete",
  "iteration": N,
  "anonymization_mapping": null,
  "team_mode": true,
  "rankings_matrix": {
    "optimist":   {"rank_given_by": {"pessimist": 5, "competitor": 4, "regulator": 3, "customer": 5}},
    "pessimist":  {"rank_given_by": {"optimist": 3, ...}},
    ...
  },
  "aggregate_ratings": {
    "optimist":   {"groundedness": 3.5, "specificity": 4.0, ...},
    ...
  }
}
```

**`critique.json`** (schema matches non-team):

```json
{
  "status": "complete",
  "iteration": N,
  "top_flaws": [
    {"persona": "optimist", "flaw_id": "F1", "effect_ref": "acq_increase", "description": "...", "resolved": true},
    ...
  ],
  "missing_variables": ["..."],
  "blind_spots_flagged": ["..."]
}
```

Author corrections accepted during debate must also be reflected in the author's `council/{short-tag}.json` file (the author rewrites it). The orchestrator **re-runs the synthesis step from `phases/simulate.md` Step 3 to Step 3.7** if any council file changed during the debate. The updated `effects-chains.json` supersedes the pre-debate version. Phase 7 CONVERGE reads the latest.

### Step 5: Ranking-flip caveat (document in output)

In team mode, cross-teammate messaging during debate can bias rankings (a teammate that was challenged and ceded ground may be ranked lower than one that pushed back successfully, regardless of analysis quality). Write into `peer-review.json`:

```json
{
  "ranking_quality_note": "Team mode: rankings are influenced by debate dynamics. Judge ranking-flip metric is informational only."
}
```

The Judge's `converge.md` already treats ranking flips as warning, not gate, so this is disclosure, not a behavioral change.

## Gates

- **Bounded debate:** Enforced mechanically by the 2-exchange cap per pair.
- **Wall-clock cap:** 10 minutes total. If exceeded, lead finalizes the phase with partial data.
- **File existence:** All 5 `peer-review/{reviewer}.json` must exist before synthesis. If a reviewer times out, their file is written with `"status": "partial"` and empty `flaws`.

## Iteration 2+ behavior

In the non-team LIGHT iteration mode, CRITIQUE is **skipped** in iteration 2+ unless convergence fails. Team mode preserves this: if Phase 7 converges at iter-2, iter-1's `critique.json` is the final critique. If convergence fails, iter-2 runs this phase again with fresh rotation pairs (optional: rotate by +1 so pair assignments differ from iter-1).

## Non-team fallback

If the lead detects at Phase 4 start that the team is unavailable (teammates died, env var changed, etc.), it falls back to `phases/critique.md` — single reviewer agent with anonymization. Write `"team_fallback_reason": "..."` into `critique.json`.
