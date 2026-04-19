"""Lock-in tests for the `assumptions_field_missing` content_check (schema v1.6).

Backstop for the iter-2 schema drift pattern where personas drop the
`assumptions` field from their council-file effects, silently crashing the
Judge's assumption_stability metric to 0%.

Real-world case: another autodecision run reported "All 5 personas in iteration
2 ignored the iter-1 schema and ... dropped the assumptions field. Broke the
Judge's assumption-stability metric to 0%. Required an entire extra iteration
3 to fix."

This validator catches it loudly so the silent failure becomes visible.

Run with:  python3 -m pytest claude-plugin/skills/autodecision/scripts/tests/
"""
from __future__ import annotations
import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE.parent / "validate-brief.py"
_SCHEMA = _HERE.parent.parent / "references" / "brief-schema.json"
_spec = importlib.util.spec_from_file_location("vb", _SCRIPT)
vb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vb)


def _make_effects_chains(per_hyp_effects: list[list[bool]]) -> dict:
    """Build a minimal effects-chains.json. per_hyp_effects[i][j] is True if
    effect j of hypothesis i should have non-empty `assumptions`, False if empty.
    """
    hyps = []
    for i, has_assums_per_effect in enumerate(per_hyp_effects):
        effects = []
        for j, has_assums in enumerate(has_assums_per_effect):
            effects.append({
                "effect_id": f"h{i}_e{j}",
                "description": f"Effect {i}.{j}",
                "order": 1,
                "probability": 0.5,
                "probability_range": [0.3, 0.7],
                "council_agreement": 3,
                "timeframe": "0-3 months",
                "assumptions": ["assumption_a"] if has_assums else [],
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


class AssumptionsFieldCheckTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(_SCHEMA.read_text())
        self.assertIn("assumptions_field_missing", self.schema["content_checks"],
                      "schema v1.6 must define assumptions_field_missing")

    def _run(self, ec: dict, mode: str = "full") -> dict:
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        (run_dir / "iteration-1").mkdir()
        (run_dir / "iteration-1" / "effects-chains.json").write_text(json.dumps(ec))
        report = vb.Report(self.schema)
        vb.check_assumptions_field_present(self.schema, run_dir, mode, report)
        for c in report.as_dict()["checks"]:
            if c["name"] == "assumptions_field_missing":
                return c
        return {}

    def test_healthy_assumptions_present_passes(self):
        """90% of effects have assumptions — clean PASS at INFO."""
        # 9 effects with assumptions, 1 without → 90%
        ec = _make_effects_chains([
            [True] * 5,
            [True] * 4 + [False] * 1,
        ])
        c = self._run(ec)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "INFO")
        self.assertEqual(c["pct_with_assumptions"], 90.0)
        self.assertEqual(c["with_assumptions"], 9)
        self.assertEqual(c["total_first_order"], 10)

    def test_partial_assumptions_warns(self):
        """40% have assumptions — above 10% fail floor, below 50% warn → WARN."""
        ec = _make_effects_chains([
            [True] * 4 + [False] * 6,  # 4/10 = 40%
        ])
        c = self._run(ec)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "WARN")
        self.assertEqual(c["pct_with_assumptions"], 40.0)

    def test_no_assumptions_hard_fails(self):
        """0% — the user's other-run pattern. Judge metric crash → HARD_FAIL."""
        ec = _make_effects_chains([
            [False] * 10,
            [False] * 5,
        ])
        c = self._run(ec)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        self.assertEqual(c["pct_with_assumptions"], 0.0)
        self.assertEqual(c["with_assumptions"], 0)
        self.assertEqual(c["total_first_order"], 15)

    def test_low_assumptions_hard_fails(self):
        """5% — below the 10% hard floor. Catastrophic drift."""
        # 1 with, 19 without → 5%
        ec = _make_effects_chains([
            [True] + [False] * 19,
        ])
        c = self._run(ec)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        self.assertEqual(c["pct_with_assumptions"], 5.0)

    def test_quick_mode_skipped(self):
        """Quick mode has no council, no synthesis — check should not run."""
        ec = _make_effects_chains([[False] * 5])
        c = self._run(ec, mode="quick")
        self.assertEqual(c, {})

    def test_missing_effects_chains_silent(self):
        """If iteration-N/effects-chains.json doesn't exist, stay silent
        (other gates handle missing data)."""
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        (run_dir / "iteration-1").mkdir()
        # No effects-chains.json
        report = vb.Report(self.schema)
        vb.check_assumptions_field_present(self.schema, run_dir, "full", report)
        for c in report.as_dict()["checks"]:
            self.assertNotEqual(c["name"], "assumptions_field_missing")

    def test_picks_latest_iteration(self):
        """When multiple iteration-N dirs exist, use the highest-numbered one
        (matches the synthesis_dedup_skipped behavior)."""
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        (run_dir / "iteration-1").mkdir()
        (run_dir / "iteration-2").mkdir()
        # iter-1: bad (no assumptions), iter-2: good (full assumptions)
        (run_dir / "iteration-1" / "effects-chains.json").write_text(
            json.dumps(_make_effects_chains([[False] * 10]))
        )
        (run_dir / "iteration-2" / "effects-chains.json").write_text(
            json.dumps(_make_effects_chains([[True] * 10]))
        )
        report = vb.Report(self.schema)
        vb.check_assumptions_field_present(self.schema, run_dir, "full", report)
        c = next(c for c in report.as_dict()["checks"]
                 if c["name"] == "assumptions_field_missing")
        # Should report on iter-2 (latest), not iter-1
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "INFO")
        self.assertIn("iteration-2", c["iteration"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
