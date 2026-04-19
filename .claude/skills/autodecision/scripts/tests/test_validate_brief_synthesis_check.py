"""Lock-in tests for the `synthesis_dedup_skipped` content check in validate-brief.py.

Catches the failure mode that shipped 3 briefs with avg_council_agreement
around 1.22-1.31 — synthesis ran the mechanical merge step but skipped
the semantic dedup of novel IDs. Each persona's near-duplicate effects sat
as separate rows with council_agreement=1, ballooning the effects map
3-5x and rendering the Effects Map's High-Confidence section empty.

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


def _make_effects_chains(per_hyp_effects: list[list[int]]) -> dict:
    """Build a minimal effects-chains.json with given council_agreement
    counts per hypothesis. e.g. [[1,1,1,2,3], [1,1,5]] = 2 hyps."""
    hyps = []
    for i, agrs in enumerate(per_hyp_effects, start=1):
        effects = []
        for j, a in enumerate(agrs):
            effects.append({
                "effect_id": f"h{i}_e{j}",
                "description": f"Effect {i}.{j}",
                "order": 1,
                "probability": 0.5,
                "probability_range": [0.3, 0.7],
                "council_agreement": a,
                "timeframe": "0-3 months",
                "assumptions": [],
                "children": [],
            })
        hyps.append({
            "hypothesis_id": f"h{i}_label",
            "label": f"H{i}",
            "statement": "...",
            "effects": effects,
        })
    return {
        "status": "complete",
        "iteration": 1,
        "decision_statement": "test",
        "hypotheses": hyps,
        "all_assumptions": {},
    }


class SynthesisDedupCheckTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(_SCHEMA.read_text())
        # Ensure the check is configured (sanity)
        self.assertIn("synthesis_dedup_skipped", self.schema["content_checks"])

    def _run_check(self, ec: dict, mode: str = "full") -> dict:
        """Run check_synthesis_dedup_quality and return the report dict for our entry."""
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        # Latest iteration is iteration-2 if both exist; the check picks the newest by N.
        # Write to iteration-1 only here so the check picks it.
        (run_dir / "iteration-1").mkdir()
        (run_dir / "iteration-1" / "effects-chains.json").write_text(json.dumps(ec))
        report = vb.Report(self.schema)
        vb.check_synthesis_dedup_quality(self.schema, run_dir, mode, report)
        for c in report.as_dict()["checks"]:
            if c["name"] == "synthesis_dedup_skipped":
                return c
        return {}

    def test_all_singletons_hard_fails(self):
        """Worst case: every effect is council_agreement=1 — synthesis skipped entirely."""
        ec = _make_effects_chains([[1] * 30, [1] * 30, [1] * 30])
        c = self._run_check(ec)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        # Should mention the avg and the percentage
        self.assertIn("1.00", c["detail"])
        self.assertIn("100.0%", c["detail"])

    def test_real_run_pattern_hard_fails(self):
        """Pattern observed in saas/vp-eng/apple runs: ~1.22-1.31 avg, ~80% singletons."""
        # Mostly 1s, sparse 2s and 3s
        ec = _make_effects_chains([
            [1] * 25 + [2] * 4 + [3] * 1,  # avg 1.24
            [1] * 25 + [2] * 4 + [3] * 1,
            [1] * 25 + [2] * 4 + [3] * 1,
        ])
        c = self._run_check(ec)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        self.assertLess(c["avg_council_agreement"], 1.5)
        self.assertGreater(c["council_agreement_one_pct"], 70)

    def test_healthy_synthesis_passes(self):
        """Effects merged across 3+ personas on average — synthesis worked."""
        # Mix of 2-5 agreement
        ec = _make_effects_chains([
            [3, 3, 4, 5, 2, 2, 3] for _ in range(5)
        ])
        c = self._run_check(ec)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "INFO")

    def test_borderline_warns(self):
        """Above hard floor (1.5) but below warn threshold (2.0)."""
        # Mix that averages ~1.7
        ec = _make_effects_chains([[1, 1, 2, 2, 3]])  # 9/5 = 1.8
        c = self._run_check(ec)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "WARN")

    def test_quick_mode_skipped(self):
        """Quick mode has no council so the check should not run at all."""
        ec = _make_effects_chains([[1] * 30])
        c = self._run_check(ec, mode="quick")
        self.assertEqual(c, {})  # check did not add an entry

    def test_picks_latest_iteration(self):
        """When multiple iteration-N dirs exist, use the highest-numbered one."""
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        (run_dir / "iteration-1").mkdir()
        (run_dir / "iteration-2").mkdir()
        # iter-1 = bad (singletons), iter-2 = good (high agreement)
        (run_dir / "iteration-1" / "effects-chains.json").write_text(
            json.dumps(_make_effects_chains([[1] * 20]))
        )
        (run_dir / "iteration-2" / "effects-chains.json").write_text(
            json.dumps(_make_effects_chains([[3, 4, 5, 4, 3]]))
        )
        report = vb.Report(self.schema)
        vb.check_synthesis_dedup_quality(self.schema, run_dir, "full", report)
        c = next(c for c in report.as_dict()["checks"] if c["name"] == "synthesis_dedup_skipped")
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "INFO")
        # Source path should reference iteration-2
        self.assertIn("iteration-2", c["source"])

    def test_missing_effects_chains_silent(self):
        """If the file isn't there at all, the check stays silent (other gates handle it)."""
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        report = vb.Report(self.schema)
        vb.check_synthesis_dedup_quality(self.schema, run_dir, "full", report)
        for c in report.as_dict()["checks"]:
            self.assertNotEqual(c["name"], "synthesis_dedup_skipped")


if __name__ == "__main__":
    unittest.main(verbosity=2)
