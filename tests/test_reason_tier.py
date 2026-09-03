"""Opt-in reason tier (phi4-mini) does not change default auto-route."""

from __future__ import annotations

import os
import unittest

from lumen_router import MODELS, route_decision


class ReasonTierTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("LUMEN_REASON_TIER", None)

    def test_auto_off_by_default(self) -> None:
        os.environ.pop("LUMEN_REASON_TIER", None)
        d = route_decision("How many apples are left after selling 19 of 47?")
        self.assertNotEqual(d["tier"], "reason")
        self.assertNotEqual(d["model"], MODELS["reason"])

    def test_auto_on_with_flag(self) -> None:
        os.environ["LUMEN_REASON_TIER"] = "1"
        d = route_decision("How many apples are left after selling 19?")
        self.assertEqual(d["tier"], "reason")
        self.assertEqual(d["model"], MODELS["reason"])

    def test_forced_tier(self) -> None:
        d = route_decision("hello", "reason")
        self.assertEqual(d["tier"], "reason")
        self.assertEqual(d["model"], "phi4-mini")
        self.assertIn("system_prompt", d)


if __name__ == "__main__":
    unittest.main()
