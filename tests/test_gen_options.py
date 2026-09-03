"""generation_options_for_tier defaults for code; keep_alive defaults."""

from __future__ import annotations

import os
import unittest

from lumen_router import (
    generation_options_for_tier,
    ollama_generate_payload,
    resolve_keep_alive,
    resolve_think,
    visible_response,
)


class GenOptionsTests(unittest.TestCase):
    def tearDown(self) -> None:
        for k in (
            "LUMEN_CODE_TEMPERATURE",
            "LUMEN_CODE_NUM_CTX",
            "LUMEN_CODE_NUM_BATCH",
            "LUMEN_KEEP_ALIVE",
            "LUMEN_THINK",
        ):
            os.environ.pop(k, None)

    def test_code_defaults(self) -> None:
        opts = generation_options_for_tier("code", num_predict=128)
        self.assertEqual(opts["temperature"], 0.1)
        self.assertEqual(opts["num_ctx"], 2048)
        self.assertEqual(opts["num_predict"], 128)

    def test_env_override(self) -> None:
        os.environ["LUMEN_CODE_NUM_CTX"] = "1024"
        os.environ["LUMEN_CODE_TEMPERATURE"] = "0"
        opts = generation_options_for_tier("code")
        self.assertEqual(opts["num_ctx"], 1024)
        self.assertEqual(opts["temperature"], 0.0)

    def test_keep_alive_default(self) -> None:
        self.assertEqual(resolve_keep_alive(), "10m")
        payload = ollama_generate_payload("llama3.2:1b", "hi")
        self.assertEqual(payload["keep_alive"], "10m")

    def test_keep_alive_off_omits(self) -> None:
        os.environ["LUMEN_KEEP_ALIVE"] = "off"
        self.assertIsNone(resolve_keep_alive())
        payload = ollama_generate_payload("llama3.2:1b", "hi")
        self.assertNotIn("keep_alive", payload)

    def test_keep_alive_zero(self) -> None:
        os.environ["LUMEN_KEEP_ALIVE"] = "0"
        self.assertEqual(resolve_keep_alive(), 0)

    def test_think_default_false(self) -> None:
        self.assertIs(resolve_think(), False)
        payload = ollama_generate_payload("llama3.2:1b", "hi")
        self.assertIs(payload["think"], False)

    def test_visible_response_strips_think(self) -> None:
        raw = "scratchpad here</think>\nTCP is reliable; UDP is best-effort."
        self.assertEqual(
            visible_response(raw),
            "TCP is reliable; UDP is best-effort.",
        )
        self.assertEqual(
            visible_response({"response": "", "thinking": "plan</think>\nfinal"}),
            "final",
        )

    def test_visible_response_strips_meta_lead(self) -> None:
        raw = (
            "The user wants a concise answer.\n\n"
            "TCP is reliable; UDP is best-effort."
        )
        self.assertEqual(visible_response(raw), "TCP is reliable; UDP is best-effort.")

    def test_visible_response_boxed(self) -> None:
        self.assertEqual(visible_response(r"thinking...\n\\boxed{40}"), "40")


if __name__ == "__main__":
    unittest.main()
