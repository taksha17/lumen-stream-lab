"""Sample NVIDIA GPU util/VRAM via nvidia-smi (stdlib). No hostnames, no secrets."""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class GpuSample:
    t_s: float
    util_pct: float | None
    mem_used_mib: float | None
    raw: str


def nvidia_smi_bin() -> str | None:
    return shutil.which("nvidia-smi")


def snapshot() -> dict[str, Any]:
    """One-shot GPU query. Empty dict if nvidia-smi missing."""
    bin_ = nvidia_smi_bin()
    if not bin_:
        return {"ok": False, "error": "nvidia-smi not in PATH"}
    try:
        out = subprocess.run(
            [
                bin_,
                "--query-gpu=name,utilization.gpu,utilization.memory,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    line = (out.stdout or "").strip().splitlines()
    if out.returncode != 0 or not line:
        err = (out.stderr or out.stdout or "nvidia-smi failed").strip()
        return {"ok": False, "error": err[:400]}
    parts = [p.strip() for p in line[0].split(",")]
    # name may contain commas — last 4 fields are numeric-ish
    if len(parts) < 5:
        return {"ok": False, "error": line[0], "raw": line[0]}
    nums = parts[-4:]
    name = ",".join(parts[:-4]).strip() or parts[0]

    def _f(s: str) -> float | None:
        try:
            return float(s)
        except ValueError:
            return None

    return {
        "ok": True,
        "name": name,
        "util_gpu_pct": _f(nums[0]),
        "util_mem_pct": _f(nums[1]),
        "memory_used_mib": _f(nums[2]),
        "memory_total_mib": _f(nums[3]),
        "note": (
            "Windows Task Manager 'GPU' often shows the 3D engine at 0% while CUDA "
            "compute is busy. Trust nvidia-smi utilization.gpu / Compute engine."
        ),
    }


class GpuSampler:
    def __init__(self, interval_s: float = 0.2) -> None:
        self.interval_s = interval_s
        self.samples: list[GpuSample] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0

    def start(self) -> None:
        if not nvidia_smi_bin():
            return
        self._t0 = time.perf_counter()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        utils = [s.util_pct for s in self.samples if s.util_pct is not None]
        mems = [s.mem_used_mib for s in self.samples if s.mem_used_mib is not None]
        return {
            "sample_count": len(self.samples),
            "interval_s": self.interval_s,
            "util_gpu_pct_max": max(utils) if utils else None,
            "util_gpu_pct_mean": round(sum(utils) / len(utils), 1) if utils else None,
            "memory_used_mib_max": max(mems) if mems else None,
            "samples": [asdict(s) for s in self.samples[:80]],
        }

    def _run(self) -> None:
        bin_ = nvidia_smi_bin()
        if not bin_:
            return
        while not self._stop.is_set():
            try:
                out = subprocess.run(
                    [
                        bin_,
                        "--query-gpu=utilization.gpu,memory.used",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                raw = (out.stdout or "").strip().splitlines()
                row = raw[0] if raw else ""
                parts = [p.strip() for p in row.split(",")]
                util = mem = None
                if len(parts) >= 2:
                    try:
                        util = float(parts[0])
                    except ValueError:
                        pass
                    try:
                        mem = float(parts[1])
                    except ValueError:
                        pass
                self.samples.append(
                    GpuSample(
                        t_s=round(time.perf_counter() - self._t0, 3),
                        util_pct=util,
                        mem_used_mib=mem,
                        raw=row,
                    )
                )
            except OSError:
                break
            self._stop.wait(self.interval_s)


def summarize_for_humans(snap: dict[str, Any], during: dict[str, Any] | None = None) -> str:
    lines: list[str] = []
    if not snap.get("ok"):
        lines.append(f"GPU: {snap.get('error', 'unavailable')}")
        lines.append("If this is an NVIDIA box, add nvidia-smi to PATH and re-run.")
        return "\n".join(lines)
    lines.append(
        f"GPU idle snapshot: {snap.get('name')}  "
        f"util={snap.get('util_gpu_pct')}%  "
        f"VRAM {snap.get('memory_used_mib')}/{snap.get('memory_total_mib')} MiB"
    )
    if during:
        lines.append(
            f"During generate: util max={during.get('util_gpu_pct_max')}% "
            f"mean={during.get('util_gpu_pct_mean')}%  "
            f"VRAM peak={during.get('memory_used_mib_max')} MiB  "
            f"({during.get('sample_count')} samples)"
        )
        umax = during.get("util_gpu_pct_max")
        if umax is not None and umax < 5 and (during.get("sample_count") or 0) >= 3:
            lines.append(
                "WARNING: GPU util stayed near 0% — Ollama is likely on CPU "
                "(or Task Manager was watching 3D, not CUDA). Check: ollama ps, "
                "CUDA driver, OLLAMA_NUM_GPU / GPU layers."
            )
    lines.append(snap.get("note", ""))
    return "\n".join(lines)
