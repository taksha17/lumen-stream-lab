"""gpu_metrics snapshot does not crash when nvidia-smi is missing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from gpu_metrics import snapshot, summarize_for_humans


class GpuMetricsTests(unittest.TestCase):
    def test_snapshot_without_smi(self) -> None:
        with patch("gpu_metrics.nvidia_smi_bin", return_value=None):
            snap = snapshot()
        self.assertFalse(snap["ok"])
        text = summarize_for_humans(snap)
        self.assertIn("nvidia-smi", text.lower())

    def test_low_util_warning(self) -> None:
        snap = {
            "ok": True,
            "name": "GPU",
            "util_gpu_pct": 0,
            "memory_used_mib": 100,
            "memory_total_mib": 4096,
            "note": "note",
        }
        during = {
            "sample_count": 10,
            "util_gpu_pct_max": 1.0,
            "util_gpu_pct_mean": 0.2,
            "memory_used_mib_max": 200,
        }
        text = summarize_for_humans(snap, during)
        self.assertIn("WARNING", text)


if __name__ == "__main__":
    unittest.main()
