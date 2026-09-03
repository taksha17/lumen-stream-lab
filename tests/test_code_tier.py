"""Experimental code tier is opt-in and must not change default 12-prompt parity."""

from __future__ import annotations

import os
import unittest

from lumen_router import route_decision


class CodeTierTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("LUMEN_CODE_TIER", None)

    def test_e07_stays_balanced_by_default(self) -> None:
        os.environ.pop("LUMEN_CODE_TIER", None)
        d = route_decision(
            "Write a Python function to compute median decode tok/s from a list of benchmark runs."
        )
        self.assertEqual(d["tier"], "balanced")
        self.assertEqual(d["model"], "lfm-balanced")

    def test_e07_code_when_enabled(self) -> None:
        os.environ["LUMEN_CODE_TIER"] = "1"
        d = route_decision(
            "Write a Python function to compute median decode tok/s from a list of benchmark runs."
        )
        self.assertEqual(d["tier"], "code")
        self.assertEqual(d["model"], "qwen2.5-coder:3b")

    def test_forced_code_tier(self) -> None:
        d = route_decision("hello", "code")
        self.assertEqual(d["tier"], "code")
        self.assertEqual(d["model"], "qwen2.5-coder:3b")


if __name__ == "__main__":
    unittest.main()
