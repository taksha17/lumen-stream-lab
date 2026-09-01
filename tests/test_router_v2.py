"""Router v2 parity with keyword router on eval suite."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from lumen_router import route_decision
from lumen_router_v2 import route_decision_v2

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "data" / "router-eval-prompts.json"


class RouterV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prompts = json.loads(PROMPTS.read_text(encoding="utf-8"))

    def test_v2_matches_teacher_tier_and_model(self) -> None:
        mismatches = []
        for entry in self.prompts:
            v1 = route_decision(entry["prompt"])
            v2 = route_decision_v2(entry["prompt"])
            if v1["tier"] != v2["tier"] or v1["model"] != v2["model"]:
                mismatches.append(
                    f"{entry['id']}: v1={v1['tier']}/{v1['model']} v2={v2['tier']}/{v2['model']}"
                )
        self.assertEqual(mismatches, [], "\n".join(mismatches))


if __name__ == "__main__":
    unittest.main()
