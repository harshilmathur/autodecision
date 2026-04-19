"""Lock-in tests for the `per_persona_overproduction` content check in validate-brief.py.

Catches the failure mode where personas write 5-8 first-order effects per hypothesis
instead of the 3 (hard cap 4) target from persona-preamble.md rule 6. This is the
upstream cause of the synthesis_dedup_skipped failure: too many singleton-island
effects pull avg council_agreement below 1.5.

The runtime enforcement is the Phase 2.5 Pre-Synthesis Discipline Gate in
simulate.md. This validator is the post-hoc backstop.

Run with:  python3 -m pytest claude-plugin/skills/autodecision/scripts/tests/
"""
from __future__ import annotations
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE.parent / "validate-brief.py"
_SCHEMA = _HERE.parent.parent / "references" / "brief-schema.json"
_spec = importlib.util.spec_from_file_location("vb", _SCRIPT)
vb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vb)


def _make_council_file(persona: str, per_hyp_first_order_counts: dict) -> dict:
    """Build a minimal persona council JSON.

    per_hyp_first_order_counts: {hypothesis_id: int} — number of 1st-order effects
    to fabricate for that hypothesis.
    """
    hyps = []
    for hyp_id, count in per_hyp_first_order_counts.items():
        effects = []
        for j in range(count):
            effects.append({
                "effect_id": f"{hyp_id}_e{j}",
                "description": f"Effect {hyp_id}.{j}",
                "order": 1,
                "probability": 0.5,
                "timeframe": "0-3 months",
                "assumptions": [],
                "children": [{
                    "effect_id": f"{hyp_id}_e{j}_c0",
                    "description": "child",
                    "order": 2,
                    "probability": 0.4,
                    "timeframe": "3-6 months",
                    "assumptions": [],
                    "parent_effect_id": f"{hyp_id}_e{j}",
                    "children": [],
                }],
            })
        hyps.append({
            "hypothesis_id": hyp_id,
            "statement": "...",
            "effects": effects,
        })
    return {"status": "complete", "persona": persona, "hypotheses": hyps}


def _make_council_dict_keyed_first_order_effects(persona: str, per_hyp_first_order_counts: dict) -> dict:
    """Shape 3 — `hypotheses` as dict keyed by id, with `first_order_effects` field.

    Real-world example: ~/.autodecision/runs/leave-unicorn-for-ai-startup/iteration-1/council/future_self.json
    """
    hyps = {}
    for hyp_id, count in per_hyp_first_order_counts.items():
        effects = []
        for j in range(count):
            effects.append({
                "effect_id": f"{hyp_id}_e{j}",
                "description": f"Effect {hyp_id}.{j}",
                # NOTE: no "order" field — first_order_effects container implies first-order
                "probability": 0.5,
                "timeframe": "0-3 months",
                "assumptions": [],
                "children": [],
            })
        hyps[hyp_id] = {"first_order_effects": effects}
    return {"persona": persona, "hypotheses": hyps}


def _make_council_effects_by_hypothesis(persona: str, per_hyp_first_order_counts: dict) -> dict:
    """Shape 2 — `effects_by_hypothesis` flat dict, no `hypotheses` field.

    Real-world example: ~/.autodecision/runs/leave-unicorn-for-ai-startup/iteration-1/council/optimist.json
    """
    ebh = {}
    for hyp_id, count in per_hyp_first_order_counts.items():
        ebh[hyp_id] = [
            {
                "effect_id": f"{hyp_id}_e{j}",
                "description": f"Effect {hyp_id}.{j}",
                "order": 1,
                "probability": 0.5,
                "timeframe": "0-3 months",
                "assumptions": [],
                "children": [],
            }
            for j in range(count)
        ]
    return {"status": "complete", "persona": persona, "effects_by_hypothesis": ebh}


def _setup_run(tmp: Path, council_files: dict, iter_n: int = 1) -> Path:
    """Create iteration-{N}/council/{persona}.json files in tmp."""
    iter_dir = tmp / f"iteration-{iter_n}"
    council_dir = iter_dir / "council"
    council_dir.mkdir(parents=True)
    for persona, data in council_files.items():
        (council_dir / f"{persona}.json").write_text(json.dumps(data))
    return tmp


class PerPersonaOverproductionCheckTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(_SCHEMA.read_text())
        self.assertIn("per_persona_overproduction", self.schema["content_checks"],
                      "schema must define per_persona_overproduction")

    def _run(self, council_files: dict, mode: str = "full", iter_n: int = 1,
             extra_iter_files: dict | None = None) -> dict:
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        _setup_run(run_dir, council_files, iter_n=iter_n)
        if extra_iter_files:
            for n, files in extra_iter_files.items():
                _setup_run(run_dir, files, iter_n=n)
        report = vb.Report(self.schema)
        vb.check_per_persona_overproduction(self.schema, run_dir, mode, report)
        for c in report.as_dict()["checks"]:
            if c["name"] == "per_persona_overproduction":
                return c
        return {}

    def test_healthy_5_per_hyp_passes(self):
        """Healthy band lower end: 5 per hypothesis. All clean."""
        council = {
            p: _make_council_file(p, {"h1": 5, "h2": 5, "h3": 5, "h4": 5, "h5": 5})
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "INFO")
        self.assertEqual(c["council_files_inspected"], 5)

    def test_tiered_analysis_7_per_hyp_passes(self):
        """v0.4.0 sell-vs-raise pattern: 7 per hyp from 4 motive tiers + 3 cash tiers.
        Threshold of WARN > 8 / HARD_FAIL > 12 must NOT false-positive on this."""
        council = {
            p: _make_council_file(p, {"h1": 7, "h2": 6, "h3": 5})
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "INFO")

    def test_at_warn_threshold_8_per_hyp_passes(self):
        """At warn threshold (8 per hypothesis) — exactly at, not over."""
        council = {
            p: _make_council_file(p, {"h1": 8, "h2": 8, "h3": 8})
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "INFO")

    def test_9_per_hyp_warns(self):
        """9 per hypothesis: above warn (8), below fail (12) → WARN."""
        council = {
            p: _make_council_file(p, {"h1": 9, "h2": 5})
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "WARN")
        # 5 personas × 1 violating hypothesis = 5 warn cells
        self.assertEqual(c["warn_count"], 5)

    def test_15_per_hyp_hard_fails(self):
        """15 per hypothesis: above hard fail (12) → HARD_FAIL.
        Catastrophic redundant invention pattern (Japan run had 30+ per persona)."""
        council = {
            p: _make_council_file(p, {"h1": 15})
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(council)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        self.assertEqual(c["fail_count"], 5)

    def test_mixed_one_persona_catastrophic_others_healthy(self):
        """One persona catastrophically over-produces, others healthy — fail on offender only."""
        council = {
            "optimist": _make_council_file("optimist", {"h1": 18, "h2": 5}),
            "pessimist": _make_council_file("pessimist", {"h1": 5, "h2": 5}),
            "competitor": _make_council_file("competitor", {"h1": 5, "h2": 5}),
            "regulator": _make_council_file("regulator", {"h1": 5, "h2": 5}),
            "customer": _make_council_file("customer", {"h1": 5, "h2": 5}),
        }
        c = self._run(council)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        self.assertEqual(c["fail_count"], 1)
        sample = c["sample_violations"][0]
        self.assertEqual(sample["persona"], "optimist")
        self.assertEqual(sample["hypothesis"], "h1")
        self.assertEqual(sample["first_order_count"], 18)

    def test_quick_mode_skipped(self):
        """Quick mode has no council — check should not run at all."""
        council = {p: _make_council_file(p, {"h1": 8}) for p in ("optimist",)}
        c = self._run(council, mode="quick")
        self.assertEqual(c, {})

    def test_no_council_files_silent(self):
        """No council/ directory at all — silent (other gates handle missing data)."""
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        # Create iteration-1 but no council dir
        (run_dir / "iteration-1").mkdir()
        report = vb.Report(self.schema)
        vb.check_per_persona_overproduction(self.schema, run_dir, "full", report)
        for c in report.as_dict()["checks"]:
            self.assertNotEqual(c["name"], "per_persona_overproduction")

    def test_inspects_all_iterations_not_just_latest(self):
        """An overstuffed iter-1 + clean iter-2 should still HARD_FAIL on iter-1.

        Iter-stability risk: iter-1 bloat surfaces just as much as iter-N bloat
        for upstream diagnosis.
        """
        iter1 = {p: _make_council_file(p, {"h1": 15}) for p in ("optimist",)}
        iter2 = {p: _make_council_file(p, {"h1": 5}) for p in ("optimist",)}
        c = self._run(iter1, mode="full", iter_n=1, extra_iter_files={2: iter2})
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        # Should reference iter-1 in the violations
        sample_iters = {v["iteration"] for v in c["sample_violations"]}
        self.assertIn("iteration-1", sample_iters)

    # ----- Schema-shape regression tests (leave-unicorn-for-ai-startup run crash) -----

    def test_dict_keyed_first_order_effects_schema_no_crash(self):
        """Real-world shape 3: hypotheses as dict-keyed, with first_order_effects
        container (no `order` field on individual effects).

        Reproduces the AttributeError from leave-unicorn-for-ai-startup run where
        the validator did `for h in data.get("hypotheses", []):` against a dict,
        iterated keys (strings), then tried h.get("effects") on the string."""
        council = {
            p: _make_council_dict_keyed_first_order_effects(p, {"h1_stay": 5, "h2_leave": 15})
            for p in ("optimist", "future_self")
        }
        # Should not crash; should HARD_FAIL on h2_leave (count=15 > cap 12)
        c = self._run(council)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        self.assertEqual(c["fail_count"], 2)  # 2 personas, both over cap on h2_leave
        sample_hyps = {v["hypothesis"] for v in c["sample_violations"]}
        self.assertIn("h2_leave", sample_hyps)

    def test_effects_by_hypothesis_flat_alt_schema(self):
        """Real-world shape 2: effects_by_hypothesis dict, no `hypotheses` field."""
        council = {
            p: _make_council_effects_by_hypothesis(p, {"h1": 5, "h2": 15})
            for p in ("market", "optimist")
        }
        c = self._run(council)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        self.assertEqual(c["fail_count"], 2)

    def test_mixed_schema_shapes_in_same_council(self):
        """One run, one iteration, mix of all 3 shapes — must not crash, must count all."""
        council = {
            "canonical_persona": _make_council_file("canonical_persona", {"h1": 5, "h2": 5}),
            "dict_keyed_persona": _make_council_dict_keyed_first_order_effects(
                "dict_keyed_persona", {"h1": 5, "h2": 5}),
            "alt_persona": _make_council_effects_by_hypothesis(
                "alt_persona", {"h1": 15, "h2": 5}),  # over the cap
        }
        c = self._run(council)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        # Only the alt_persona on h1 violates
        self.assertEqual(c["fail_count"], 1)
        v = c["sample_violations"][0]
        self.assertEqual(v["persona"], "alt_persona")
        self.assertEqual(v["hypothesis"], "h1")

    def test_universal_helper_returns_correct_first_order_counts(self):
        """Direct unit test on the helper — all 3 shapes return matching counts."""
        # Same logical content (h1: 3 effects, h2: 5 effects) in 3 different schemas
        canonical = _make_council_file("p", {"h1": 3, "h2": 5})
        dict_keyed = _make_council_dict_keyed_first_order_effects("p", {"h1": 3, "h2": 5})
        alt = _make_council_effects_by_hypothesis("p", {"h1": 3, "h2": 5})

        for label, data in (("canonical", canonical), ("dict_keyed", dict_keyed), ("alt", alt)):
            extracted, recognized = vb._extract_first_order_per_hyp(data)
            self.assertTrue(recognized, f"{label}: shape should be recognized")
            self.assertEqual(len(extracted["h1"]), 3, f"{label}: h1 count mismatch")
            self.assertEqual(len(extracted["h2"]), 5, f"{label}: h2 count mismatch")

    def test_helper_skips_malformed_silently(self):
        """Garbage input must not crash. `recognized` reflects OUTER shape match;
        bad inner content yields empty per-hypothesis lists (not crash)."""
        # Outer shape NOT recognized: empty, wrong-type top-level fields
        unrecognized_cases = [
            {},  # empty
            {"hypotheses": "this is a string not a list or dict"},
            {"effects_by_hypothesis": "not a dict"},
            {"random_field": [1, 2, 3]},
        ]
        for i, data in enumerate(unrecognized_cases):
            extracted, recognized = vb._extract_first_order_per_hyp(data)
            self.assertFalse(recognized, f"unrecognized case {i}: should NOT be recognized")
            self.assertEqual(extracted, {}, f"unrecognized case {i}: should be empty")

        # Outer shape RECOGNIZED but inner garbage: must not crash, yields empty/sparse output
        recognized_but_garbage = [
            {"hypotheses": [None, None]},
            {"hypotheses": ["just_id_strings"]},
            {"hypotheses": {"h1": "not a dict or list"}},
            {"hypotheses": {"h1": {}}},  # dict-keyed but no effects field
            {"effects_by_hypothesis": {"h1": "garbage"}},
        ]
        for i, data in enumerate(recognized_but_garbage):
            extracted, recognized = vb._extract_first_order_per_hyp(data)
            self.assertTrue(recognized, f"recognized-garbage case {i}: outer shape should match")
            for hid, effs in extracted.items():
                self.assertIsInstance(effs, list, f"case {i}: effects must be list")
                self.assertEqual(effs, [], f"case {i}: garbage inner yields empty list")

    # ----- Schema variant 4: 'first_order' field name (saas-founder-20m run) -----

    def test_dict_keyed_first_order_field_name(self):
        """Real-world shape 4: dict-keyed hypotheses with `first_order` field
        (NOT `first_order_effects`) — observed in saas-founder-20m-strategic-invest run."""
        # Build manually since helper builders use first_order_effects
        data = {
            "persona": "regulator",
            "hypotheses": {
                "h1": {"first_order": [
                    {"effect_id": "h1_e0", "description": "x", "probability": 0.5,
                     "timeframe": "0-3 months", "assumptions": [], "children": []}
                    for _ in range(3)
                ]},
                "h2": {"first_order": [
                    {"effect_id": "h2_e0", "description": "x", "probability": 0.5,
                     "timeframe": "0-3 months", "assumptions": [], "children": []}
                    for _ in range(15)  # over the cap
                ]},
            },
        }
        extracted, recognized = vb._extract_first_order_per_hyp(data)
        self.assertTrue(recognized)
        self.assertEqual(len(extracted["h1"]), 3)
        self.assertEqual(len(extracted["h2"]), 15)

        # End-to-end through check_per_persona_overproduction
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        (run_dir / "iteration-1" / "council").mkdir(parents=True)
        (run_dir / "iteration-1" / "council" / "regulator.json").write_text(json.dumps(data))
        report = vb.Report(self.schema)
        vb.check_per_persona_overproduction(self.schema, run_dir, "full", report)
        c = next(c for c in report.as_dict()["checks"] if c["name"] == "per_persona_overproduction")
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        # Should have detected h2 = 15 violation
        sample_hyps = {v["hypothesis"] for v in c["sample_violations"]}
        self.assertIn("h2", sample_hyps)

    # ----- Unknown-shape WARN (silent miss is now visible) -----

    def test_unknown_shape_logs_warn(self):
        """Council file with unknown shape should produce WARN, not silent skip."""
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        (run_dir / "iteration-1" / "council").mkdir(parents=True)
        # Write a valid council in a known shape
        (run_dir / "iteration-1" / "council" / "good.json").write_text(
            json.dumps(_make_council_file("good", {"h1": 5}))
        )
        # Write a council in unrecognized shape
        weird_shape = {
            "persona": "weird",
            "iteration": 1,
            "novel_field_we_dont_handle": {"h1": ["effect1", "effect2"]},
        }
        (run_dir / "iteration-1" / "council" / "weird.json").write_text(json.dumps(weird_shape))
        report = vb.Report(self.schema)
        vb.check_per_persona_overproduction(self.schema, run_dir, "full", report)
        # Should produce a WARN entry mentioning unknown shape
        warns = [c for c in report.as_dict()["checks"]
                 if c["name"] == "per_persona_overproduction" and c["severity"] == "WARN"]
        self.assertTrue(any("unknown_shape_count" in w for w in warns) or
                        any("unrecognized" in w["detail"].lower() for w in warns),
                        "Unknown-shape council file should produce a WARN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
