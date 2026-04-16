<!--
phase: 8.5
phase_name: VALIDATE-BRIEF
runs_in:
  - full       (mandatory — runs after Phase 8 writes DECISION-BRIEF.md)
  - medium     (mandatory)
  - quick      (mandatory in --mode quick — reduced section set, still enforces no-snake-case + recommendation-position)
  - revise     (mandatory — same as full)
  - challenge  (SKIPPED — different output format, no schema yet)
reads:
  - ~/.autodecision/runs/{slug}/DECISION-BRIEF.md
  - references/brief-schema.json (canonical structure per mode)
  - ~/.autodecision/runs/{slug}/iteration-*/effects-chains.json (for cross-ref coverage)
  - ~/.autodecision/runs/{slug}/iteration-*/adversary.json (for ref:ID coverage)
  - ~/.autodecision/runs/{slug}/convergence-log.json (for convergence row count)
  - ~/.autodecision/runs/{slug}/config.json (for mode)
runs_inline:
  - Mechanical Python script (scripts/validate-brief.py) — never an LLM agent
writes:
  - ~/.autodecision/runs/{slug}/validation-report.json
gates:
  - Exit 0 (clean)     → continue to print
  - Exit 1 (warn)      → continue, append validation footer
  - Exit 2 (HARD_FAIL) → re-prompt DECIDE ONCE; if still failing, prepend VALIDATION_FAILED warning
  - Exit 3 (script err)→ log stderr, continue (never block the user)
canonical_rules:
  - Full rule definitions live in references/validation.md Rule 13
  - This file is the invocation recipe + exit-code dispatch only
-->

# Phase 8.5: VALIDATE-BRIEF

## Purpose

Mechanical post-flight check on `DECISION-BRIEF.md`. The DECIDE agent does not self-check the brief it just produced; this phase enforces structural compliance in ~100ms via a Python script driven by the canonical schema.

**Full rule definitions:** `references/validation.md` Rule 13 — what's checked, severity table, hard-fail vs warn classification. Read that for the "what." This file is the "how to invoke."

## NON-NEGOTIABLE: No inline custom validators

Phase 8.5 is executing `scripts/validate-brief.py` against `references/brief-schema.json`.
It is NOT writing a new Python script, inline in Bash, that checks for the section
headers you authored five minutes ago in DECIDE. That is self-certification — a
writer who invented `## Context` and `## Decision tilt` will happily write a
validator asking "is `## Context` present?" and declare 13/13 passed. The brief is
still broken; the writer just graded its own paper.

If the named validator can't run (e.g., `python3` missing), fall through to the
structural self-check written out in `phases/decide.md` Step 5.5. That is a prose
re-read of the brief against the Step 4a checklist. It is not an ad-hoc Python
script. Do not write inline validators. Ever.

## Invocation

```bash
python3 "{skill_dir}/scripts/validate-brief.py" \
  --run-dir "{run_dir}" \
  --schema  "{skill_dir}/references/brief-schema.json" \
  --mode    "{mode}"
```

`{mode}` derives from `config.json > iterations`: `0 = quick`, `1 = medium`, `2+ = full`. Revise runs use `full`. Challenge runs skip this phase entirely.

`{skill_dir}` is the directory this phase file lives under (one level up from `references/phases/`). Plugin installs resolve to `<plugin>/skills/autodecision/`; vendored installs resolve to `.claude/skills/autodecision/` or `~/.claude/skills/autodecision/`.

## Exit-Code Dispatch

| Exit | Meaning | Action |
|------|---------|--------|
| 0 | All checks passed | Continue to DECIDE Step 6 (print brief) |
| 1 | Warnings only | Continue, append validation footer to brief |
| 2 | **HARD_FAIL** — structural issue | Re-prompt DECIDE ONCE with the violations. If retry also hard-fails, fall through with VALIDATION_FAILED. |
| 3 | Script error | Log `Validator failed: {stderr}`. Continue. Never block a run on a broken validator. |

## Hard-Fail Recovery (one retry only)

On exit 2, read `validation-report.json`, build a corrective prompt from the HARD_FAIL entries, and re-invoke DECIDE inline (NOT as a new Agent):

```
The Decision Brief failed mechanical validation. Rewrite DECISION-BRIEF.md
fixing ONLY these specific issues — do not change content that passed:

{for each HARD_FAIL: check_name, location, expected, got, one-line fix}

Keep the trailing <!-- validator-refs: --> block — it is required for cross-reference tracking.
Then I will re-run validation.
```

Re-run the validator after the rewrite. If it ALSO returns exit 2:

1. Do NOT retry a third time.
2. Prepend this banner to `DECISION-BRIEF.md`:
   > ⚠️ **VALIDATION_FAILED** — this brief did not pass mechanical structural checks
   > after one retry. Specific failures listed at the end in "Appendix V: Validation
   > Report." Treat section headers, ordering, and cross-references with extra scrutiny.
3. Append `validation-report.json` (pretty-printed) as "Appendix V: Validation Report" at the end.
4. Print to user: "Brief failed structural validation after one retry. Flagged in header."
5. Continue to journal persistence — flagged briefs are still logged (useful for debugging the validator itself).

## Warning Footer

On exit 1, append to the bottom of the printed brief:
```
---
_Validation: {N} warning(s). See {run_dir}/validation-report.json for details._
```

## Integration Point in DECIDE

Inserts as **Step 5.5** in `phases/decide.md`, between Step 5 (persist to journal) and Step 6 (print brief). Order is deliberate: persist first so a failed brief is still in the journal; validate before the user sees it.

## Schema Source-of-Truth

Schema: `references/brief-schema.json`. Script: `scripts/validate-brief.py`. Both are canonical — change one, change the other in the same commit. The schema describes intent; the script enforces it. If `output-format.md` (the human-facing template) drifts from the schema, the schema wins.
