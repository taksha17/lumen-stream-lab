"""Validate checked-in benchmark fixtures (stdlib only)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "results" / "fixtures"
REF_LAB = ROOT / "hardware" / "reference-lab.json"


class TestFixtures(unittest.TestCase):
    def test_phase_d3_summary(self) -> None:
        path = FIXTURES / "phase-d3-summary.json"
        self.assertTrue(path.exists(), "phase-d3-summary.json missing")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("phase"), "D3")
        results = data.get("results") or []
        self.assertGreaterEqual(len(results), 9)
        by_id = {r["id"]: r for r in results}
        self.assertIn("BL-02", by_id)
        baseline = by_id["BL-02"]["median_decode_tok_s"]
        self.assertGreater(baseline, 40)
        smol = by_id.get("D3-02", {}).get("median_decode_tok_s", 0)
        self.assertGreater(smol, 90)

    def test_ecosystem_comparison(self) -> None:
        path = FIXTURES / "ecosystem-comparison-20260901.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        orch = data["lumen_orchestration_mean_tok_s"]
        gain = data["lumen_gain_vs_canonical_pct"]
        self.assertGreaterEqual(orch, 67.73)
        self.assertGreaterEqual(gain, 40.0)
        self.assertTrue(data["lumen_pass_40pct"])

    def test_reference_lab_profile(self) -> None:
        data = json.loads(REF_LAB.read_text(encoding="utf-8"))
        mb = data["measured_baselines"]
        self.assertGreaterEqual(mb["orchestration_mean_tok_s"], 68.0)
        self.assertGreaterEqual(mb["orchestration_gain_pct_vs_48_38"], 40.0)
        self.assertIn("fixtures", data)

    def test_router_eval_summary(self) -> None:
        path = FIXTURES / "router-eval-summary.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("routing_accuracy"), "12/12")

    def test_fast_tier_candidate_gate(self) -> None:
        path = FIXTURES / "fast-tier-candidate-gate.json"
        self.assertTrue(path.exists())
        rows = json.loads(path.read_text(encoding="utf-8"))
        smol = next(r for r in rows if "smollm2" in r["model"])
        self.assertFalse(smol["promote_candidate"])


if __name__ == "__main__":
