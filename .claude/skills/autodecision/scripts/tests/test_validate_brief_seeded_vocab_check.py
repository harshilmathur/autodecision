"""Lock-in tests for the `seeded_vocab_ignored` content check in validate-brief.py.

Catches the failure mode where personas got the seeded `expected_effect_ids`
in shared-context.md but ignored them entirely — wrote their own descriptive
IDs (e.g. seeded `earnout_lock_in_risk` becomes `earnout_and_retention_claw_back_value`
across all personas, with NO match to the seeded form).

The seeded vocabulary mechanism is supposed to make ~80% of synthesis mechanical
(5 personas converging on the same 4 seeded IDs synthesizes by exact effect_id
match). When personas invent variants, each invented ID becomes a singleton
island and dedup must work much harder.

Sell-15m-vs-safe-30m run had 0/16 = 0% adoption — silent regression caught
only by manual inspection of council files.

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


def _make_hypotheses_json(seeded_per_hyp: dict[str, list[str]]) -> dict:
    """Build a minimal hypotheses.json with given seeded effect_ids per hypothesis."""
    return {
        "status": "complete",
        "hypotheses": [
            {
                "hypothesis_id": hid,
                "statement": f"Statement for {hid}",
                "expected_effect_ids": seeded,
            }
            for hid, seeded in seeded_per_hyp.items()
        ],
    }


def _make_council_canonical(persona: str, ids_per_hyp: dict[str, list[str]]) -> dict:
    """Build a council file in the canonical hypotheses[] schema."""
    return {
        "status": "complete",
        "persona": persona,
        "hypotheses": [
            {
                "hypothesis_id": hid,
                "statement": "...",
                "effects": [
                    {
                        "effect_id": eid,
                        "description": eid.replace("_", " "),
                        "order": 1,
                        "probability": 0.5,
                        "timeframe": "0-3 months",
                        "assumptions": [],
                        "children": [],
                    }
                    for eid in ids
                ],
            }
            for hid, ids in ids_per_hyp.items()
        ],
    }


def _make_council_alt(persona: str, ids_per_hyp: dict[str, list[str]]) -> dict:
    """Build a council file in the alt effects_by_hypothesis{} schema."""
    return {
        "status": "complete",
        "persona": persona,
        "effects_by_hypothesis": {
            hid: [
                {
                    "effect_id": eid,
                    "description": eid.replace("_", " "),
                    "order": 1,
                    "probability": 0.5,
                    "timeframe": "0-3 months",
                    "assumptions": [],
                    "children": [],
                }
                for eid in ids
            ]
            for hid, ids in ids_per_hyp.items()
        },
    }


def _setup_run(tmp: Path, seeded: dict, council: dict, schema: str = "canonical",
               iter_n: int = 1) -> Path:
    """Create iteration-{N}/ with hypotheses.json + council/{persona}.json."""
    iter_dir = tmp / f"iteration-{iter_n}"
    council_dir = iter_dir / "council"
    council_dir.mkdir(parents=True)
    (iter_dir / "hypotheses.json").write_text(json.dumps(_make_hypotheses_json(seeded)))
    builder = _make_council_canonical if schema == "canonical" else _make_council_alt
    for persona, ids_per_hyp in council.items():
        (council_dir / f"{persona}.json").write_text(
            json.dumps(builder(persona, ids_per_hyp))
        )
    return tmp


class SeededVocabCheckTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(_SCHEMA.read_text())
        self.assertIn("seeded_vocab_ignored", self.schema["content_checks"],
                      "schema must define seeded_vocab_ignored")

    def _run(self, seeded, council, mode="full", schema="canonical") -> dict:
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        _setup_run(run_dir, seeded, council, schema=schema)
        report = vb.Report(self.schema)
        vb.check_seeded_vocab_adoption(self.schema, run_dir, mode, report)
        for c in report.as_dict()["checks"]:
            if c["name"] == "seeded_vocab_ignored":
                return c
        return {}

    def test_full_adoption_passes(self):
        """100% adoption: every persona uses every seeded ID."""
        seeded = {"h1": ["a", "b", "c", "d"], "h2": ["e", "f", "g"]}
        council = {
            p: {"h1": ["a", "b", "c"], "h2": ["e", "f", "g"]}
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "INFO")
        # 6 of 7 seeded used (h1 has 4 seeded but personas use only 3 of them — d is unused)
        self.assertEqual(c["seeded_used"], 6)
        self.assertEqual(c["total_seeded"], 7)

    def test_partial_adoption_warns(self):
        """30-40% adoption: WARN but not HARD_FAIL."""
        seeded = {"h1": ["a", "b", "c", "d"], "h2": ["e", "f", "g", "h"]}
        # Personas use 'a' from h1 and 'e' from h2 — 2/8 = 25% adoption (FAIL)
        # Bump to 3/8 = 37.5% (WARN, above 20% fail floor, below 50% warn floor)
        council = {
            p: {"h1": ["a", "x"], "h2": ["e", "f", "y"]}
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "WARN")
        self.assertLess(c["adoption_pct"], 50)
        self.assertGreaterEqual(c["adoption_pct"], 20)

    def test_zero_adoption_hard_fails(self):
        """Sell-15m-vs-safe-30m pattern: 0% seeded usage → HARD_FAIL."""
        seeded = {"h1": ["a", "b", "c", "d"], "h2": ["e", "f", "g", "h"]}
        council = {
            p: {"h1": ["x1", "x2", "x3"], "h2": ["y1", "y2", "y3"]}
            for p in ("optimist", "pessimist", "competitor", "regulator", "customer")
        }
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")
        self.assertEqual(c["adoption_pct"], 0)
        self.assertEqual(c["seeded_used"], 0)
        self.assertIn("0/8", c["detail"])

    def test_low_adoption_hard_fails(self):
        """10% adoption (below 20% floor) → HARD_FAIL."""
        seeded = {"h1": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]}
        # Only one ID 'a' used → 1/10 = 10% adoption
        council = {
            p: {"h1": ["a", "x", "y"]}
            for p in ("optimist", "pessimist")
        }
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")

    def test_alt_schema_effects_by_hypothesis(self):
        """Validator must handle the effects_by_hypothesis{} schema shape."""
        seeded = {"h1": ["a", "b", "c"]}
        council = {
            p: {"h1": ["x1", "x2"]}  # 0% adoption
            for p in ("optimist", "pessimist", "competitor")
        }
        c = self._run(seeded, council, schema="alt")
        self.assertEqual(c["status"], "FAIL")
        self.assertEqual(c["severity"], "HARD_FAIL")

    def test_quick_mode_skipped(self):
        """Quick mode has no council — check should not run."""
        seeded = {"h1": ["a", "b"]}
        council = {"optimist": {"h1": ["x"]}}
        c = self._run(seeded, council, mode="quick")
        self.assertEqual(c, {})

    def test_no_seeded_warns(self):
        """If hypotheses.json has no expected_effect_ids at all, warn."""
        seeded = {"h1": [], "h2": []}
        council = {p: {"h1": ["x"], "h2": ["y"]} for p in ("optimist",)}
        c = self._run(seeded, council)
        self.assertEqual(c["status"], "PASS")
        self.assertEqual(c["severity"], "WARN")
        self.assertIn("No seeded", c["detail"])

    def test_seeded_extractor_accepts_both_id_and_hypothesis_id(self):
        """Real-world: saas-founder iter-1 hypotheses.json used `id` instead of
        `hypothesis_id`. The seeded extractor must accept both names."""
        # Canonical: hypothesis_id
        canonical = {"hypotheses": [
            {"hypothesis_id": "h1", "expected_effect_ids": ["a", "b", "c"]},
        ]}
        out = vb._extract_seeded_per_hyp(canonical)
        self.assertEqual(out["h1"], ["a", "b", "c"])

        # Alt: id
        alt = {"hypotheses": [
            {"id": "h2", "expected_effect_ids": ["x", "y"]},
        ]}
        out = vb._extract_seeded_per_hyp(alt)
        self.assertEqual(out["h2"], ["x", "y"])

        # Both present — hypothesis_id wins (canonical takes precedence)
        both = {"hypotheses": [
            {"hypothesis_id": "h_canonical", "id": "h_alt", "expected_effect_ids": ["z"]},
        ]}
        out = vb._extract_seeded_per_hyp(both)
        self.assertIn("h_canonical", out)
        self.assertNotIn("h_alt", out)

        # Neither present — skip the entry (don't crash)
        missing = {"hypotheses": [
            {"expected_effect_ids": ["w"]},  # no id at all
        ]}
        out = vb._extract_seeded_per_hyp(missing)
        self.assertEqual(out, {})

    def test_iter1_fallback_when_iter2_uses_carryforward_schema(self):
        """Iter-2 hypotheses.json uses carryforward schema (carried_over /
        new_in_iter_2 instead of hypotheses[]). Check must fall back to iter-1's
        seeded vocab rather than warning 'no seeded'.

        Real-world case: ~/.autodecision/runs/saas-founder-20m-strategic-invest/
        had iter-1 hypotheses.json with 5 seeded per hyp, iter-2 with carryforward
        schema. Old check warned 'No seeded effect_ids' (false signal). New check
        should find iter-1's seeded vocab and measure adoption against latest
        iter's council files.
        """
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        run_dir = Path(d.name)
        # iter-1: canonical hypotheses.json with seeded IDs
        iter1 = run_dir / "iteration-1"
        (iter1 / "council").mkdir(parents=True)
        (iter1 / "hypotheses.json").write_text(json.dumps(_make_hypotheses_json(
            {"h1": ["a", "b", "c", "d"]}
        )))
        (iter1 / "council" / "optimist.json").write_text(
            json.dumps(_make_council_canonical("optimist", {"h1": ["a", "x"]}))
        )
        # iter-2: carryforward schema (no `hypotheses[]`) + council that uses
        # iter-1's seeded vocab properly
        iter2 = run_dir / "iteration-2"
        (iter2 / "council").mkdir(parents=True)
        (iter2 / "hypotheses.json").write_text(json.dumps({
            "status": "complete",
            "iteration": 2,
            "carried_over": ["h1"],
            "new_in_iter_2": [],
            "iter1_vocabulary_summary": "see iter-1 hypotheses.json"
        }))
        # iter-2 council uses 4/4 seeded IDs from iter-1
        (iter2 / "council" / "optimist.json").write_text(
            json.dumps(_make_council_canonical("optimist", {"h1": ["a", "b", "c", "d"]}))
        )
        report = vb.Report(self.schema)
        vb.check_seeded_vocab_adoption(self.schema, run_dir, "full", report)
        c = next(c for c in report.as_dict()["checks"] if c["name"] == "seeded_vocab_ignored")
        # Should find iter-1's seeded vocab, not warn 'no seeded'
        self.assertNotIn("No seeded", c["detail"])
        self.assertEqual(c["total_seeded"], 4)
        # iter-2 council has 4/4 = 100% adoption
        self.assertEqual(c["adoption_pct"], 100.0)
        self.assertEqual(c["seeded_source_iteration"], "iteration-1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
