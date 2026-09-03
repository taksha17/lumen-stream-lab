# Product roadmap — scale & tune (promotion deferred)

Social / HN / Reddit: **paused**. Focus is measurable product gains on the reference 4GB lab and portable config.

## Non‑negotiables

1. Hybrid auto-route **12/12** parity stays green.
2. Orchestration mean stays **≥ +40%** vs always-3B (canonical 48.38).
3. New tiers stay **opt-in** until benches pass (`LUMEN_*` flags).
4. No secrets / lab IPs / tokens in git.

## Now (this cycle)

| Priority | Work | Why |
|----------|------|-----|
| **P0** | Probe **fast** swap: `llama3.2:1b` vs `qwen3:1.7b` | Higher floor tok/s lifts hybrid mean |
| **P0** | Domain **delta**: stock `qwen2.5:3b-instruct` vs `qwen2.5-3b-lumen` | Prove S07 still earns its slot |
| **P1** | Re-run orchestration / regression on lab after any swap | Gate before shipping defaults |
| **P1** | Reduce tier-switch thrash (`keep_alive`, unload policy) | Wall time when chatting across tiers |

## Next (after P0/P1)

| Priority | Work | Why |
|----------|------|-----|
| **P2** | Balanced probe: LFM vs `qwen3:4b` / `phi4-mini` (fit + tok/s) | Only if VRAM + mean allow |
| **P2** | Router v2 A/B behind flag | Better routing without breaking keyword gate |
| **P3** | Vision / image_gen | Parked on 4GB — needs spare VRAM or mid-class GPU |

## Explicitly not now

- Auto `LUMEN_CODE_TIER=1` (coder slower than LFM on 1650)
- Show HN / LocalLLaMA pushes ([PROMOTE.md](./PROMOTE.md) parked)
- Resident 7B/8B as balanced default

Track benches in [UPGRADES.md](../UPGRADES.md). Script: `scripts/probe_tier_swaps.py`.
