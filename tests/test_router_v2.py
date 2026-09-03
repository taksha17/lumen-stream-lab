"""Router v2 parity + LUMEN_ROUTER flag."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from lumen_router import resolve_router_engine, route_decision, route_with_engine
from lumen_router_v2 import route_decision_v2

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "data" / "router-eval-prompts.json"


class RouterV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prompts = json.loads(PROMPTS.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        os.environ.pop("LUMEN_ROUTER", None)

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

    def test_resolve_router_engine_env(self) -> None:
        self.assertEqual(resolve_router_engine(), "keyword")
        os.environ["LUMEN_ROUTER"] = "v2"
        self.assertEqual(resolve_router_engine(), "v2")

    def test_route_with_engine_tags_router(self) -> None:
        prompt = "What is 2+2?"
        k = route_with_engine(prompt, engine="keyword")
        v = route_with_engine(prompt, engine="v2")
        self.assertEqual(k["router"], "keyword")
        self.assertEqual(v["router"], "v2")
        self.assertEqual(k["model"], v["model"])


if __name__ == "__main__":
    unittest.main()
