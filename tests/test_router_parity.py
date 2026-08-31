"""Router parity: Python decisions match eval suite expectations."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from lumen_router import route_decision, wrap_domain_prompt

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "data" / "router-eval-prompts.json"


class RouterParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prompts = json.loads(PROMPTS.read_text(encoding="utf-8"))

    def test_eval_suite_routing_accuracy(self) -> None:
        mismatches = []
        for entry in self.prompts:
            decision = route_decision(entry["prompt"])
            if decision["tier"] != entry["expected_auto_tier"]:
                mismatches.append(
                    f"{entry['id']}: expected {entry['expected_auto_tier']}, got {decision['tier']}"
                )
        self.assertEqual(mismatches, [], "\n".join(mismatches))

    def test_e05_routes_to_domain_model(self) -> None:
        decision = route_decision("When should Lumen route to a 1B vs 3B vs 7B model?")
        self.assertEqual(decision["tier"], "balanced")
        self.assertEqual(decision["model"], "qwen2.5-3b-lumen")

    def test_e12_includes_system_prompt(self) -> None:
        decision = route_decision("What is Lumen Stream Lab?")
        self.assertIn("system_prompt", decision)
        self.assertIn("orchestrat", decision["system_prompt"].lower())

    def test_routing_prefix_for_tiers(self) -> None:
        wrapped = wrap_domain_prompt("When should Lumen route to a 1B vs 3B vs 7B model?")
        self.assertIn("fast", wrapped.lower())
        self.assertIn("1b", wrapped.lower())


if __name__ == "__main__":
    unittest.main()
