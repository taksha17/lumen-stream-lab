#!/usr/bin/env python3
"""Compare baseline vs optimized benchmark medians. Exit 0 if gain >= target."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check if speed improvement meets target")
    parser.add_argument("--baseline", type=float, required=True, help="Baseline median tok/s")
    parser.add_argument("--optimized", type=float, required=True, help="Optimized median tok/s")
    parser.add_argument("--min-gain", type=float, default=0.40, help="Minimum fractional gain (0.40 = 40%%)")
    args = parser.parse_args()

    if args.baseline <= 0:
        print("ERROR: baseline must be > 0", file=sys.stderr)
        return 2

    gain = (args.optimized - args.baseline) / args.baseline
    target = args.optimized / args.baseline
    passed = gain >= args.min_gain

    print(f"Baseline:   {args.baseline:.2f} tok/s")
    print(f"Optimized:  {args.optimized:.2f} tok/s")
    print(f"Gain:       {gain * 100:.1f}%")
    print(f"Target:     ≥ {args.min_gain * 100:.0f}% (need ≥ {args.baseline * (1 + args.min_gain):.2f} tok/s)")
    print(f"Result:     {'PASS ✓' if passed else 'FAIL ✗'}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
