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
| **P0** | Probe **fast** swap: `llama3.2:1b` vs `qwen3:1.7b` | **Done** — keep 1B (96 vs 86 tok/s) |
| **P0** | Domain **delta**: stock 3B vs `qwen2.5-3b-lumen` | **Done** — keep lumen (quality); tok/s tied |
| **P1** | Re-run orchestration / regression on lab | **Done** — PASS, mean **69.12** then post-LFM **68.03** (**+40.6%**) |
| **P1** | Reduce tier-switch thrash (`keep_alive`) | **Done** — default `10m`; same-tier wall −42%; cross-tier no win on 4GB |

## Next (after P0/P1)

| Priority | Work | Why |
|----------|------|-----|
| **P2** | Balanced probe: LFM vs `qwen3:4b` / `phi4-mini` / gemma3 | **Done** — keep LFM (65 vs ≤30 tok/s); Modelfile + `think:false` tune |
| **P2** | Router v2 A/B behind flag | **Done** — `LUMEN_ROUTER=v2` opt-in; eval+holdout 22/22 match; default stays keyword |
| **P2** | LFM answer quality | **Done** — meta strip + num_predict 192; ChatML template inherit |
| **P2** | Opt-in `reason` tier (`phi4-mini`) | **Done** — `LUMEN_REASON_TIER=1` / `--tier reason` |
| **P2** | Router v3 from real logs | **In progress** — `route-log.jsonl` + `LUMEN_ROUTER=v3` |
| **P3** | Vision / image_gen | Parked on 4GB — needs spare VRAM or mid-class GPU |

## Explicitly not now

- Auto `LUMEN_CODE_TIER=1` (coder slower than LFM on 1650)
- Auto `LUMEN_REASON_TIER=1` (phi4 ~30 tok/s vs LFM ~65)
- Show HN / LocalLLaMA pushes ([PROMOTE.md](./PROMOTE.md) parked)
- Resident 7B/8B as balanced default

Track benches in [UPGRADES.md](../UPGRADES.md). Script: `scripts/probe_tier_swaps.py`.
