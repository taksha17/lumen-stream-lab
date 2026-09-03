"""generation_options_for_tier defaults for code."""

from __future__ import annotations

import os
import unittest

from lumen_router import generation_options_for_tier


class GenOptionsTests(unittest.TestCase):
    def tearDown(self) -> None:
        for k in ("LUMEN_CODE_TEMPERATURE", "LUMEN_CODE_NUM_CTX", "LUMEN_CODE_NUM_BATCH"):
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


if __name__ == "__main__":
    unittest.main()
