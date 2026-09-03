"""Router v3 train + engine smoke."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class RouteLogTests(unittest.TestCase):
    def test_append_and_feedback(self) -> None:
        sys_path = str(ROOT / "scripts")
        import sys

        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        from route_log import append_route_event, feedback_last, read_events, stats

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "route-log.jsonl"
            os.environ["LUMEN_ROUTE_LOG"] = "1"
            os.environ["LUMEN_ROUTE_LOG_PATH"] = str(path)
            rec = append_route_event(
                prompt="What is 2+2?",
                tier="fast",
                model="llama3.2:1b",
                reason="test",
                source="unit",
                tok_s=100.0,
            )
            self.assertIsNotNone(rec)
            self.assertEqual(len(read_events(path)), 1)
            last = feedback_last("up", path)
            self.assertEqual(last["feedback"], "up")
            st = stats(path)
            self.assertEqual(st["n"], 1)
            self.assertEqual(st["with_feedback"], 1)
        os.environ.pop("LUMEN_ROUTE_LOG_PATH", None)


class RouterV3EngineTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("LUMEN_ROUTER", None)

    def test_resolve_v3(self) -> None:
        from lumen_router import resolve_router_engine

        os.environ["LUMEN_ROUTER"] = "v3"
        self.assertEqual(resolve_router_engine(), "v3")

    def test_weights_roundtrip_if_present(self) -> None:
        weights = ROOT / "data" / "router-v3-weights.json"
        if not weights.exists():
            self.skipTest("router-v3-weights.json not trained yet")
        from lumen_router import route_with_engine

        d = route_with_engine("What is 2+2?", engine="v3")
        self.assertEqual(d["router"], "v3")
        self.assertEqual(d["tier"], "fast")


if __name__ == "__main__":
    unittest.main()
