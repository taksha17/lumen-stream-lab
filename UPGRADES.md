# UPGRADES.md — Lumen Stream Lab

Track every **model swap, capability addition, or router expansion** here.
Separate from `docs/RESULTS.md` (bench numbers) and `docs/internal/STATUS.md` (session state).

Format per entry:
- Date
- Change type (model / capability / backend)
- Tier affected
- Reason
- Bench result vs prior
- Status (proposed / in-progress / shipped / rolled-back)

---

## Open proposals (not yet started)

### 2026-09-03 — Multi-modal scope expansion
- **Type:** capability
- **Tiers:** `vision_qa`, `image_gen` (code tier **shipped opt-in** — see Shipped / in-progress history)
- **Reason:** coding path exists; vision/image still blocked by 4GB VRAM headroom.
- **Plan:** park until mid-VRAM contributor profile or spare resident budget.
- **Status:** proposed — deferred

### 2026-09-03 — Candidate models to probe (Tier 1, resident)
| Model | Slot | Expected role |
|---|---|---|
| `Qwen3-4B-Instruct-2507` | `balanced` | Replacement candidate for LFM / mid tier |
| `Qwen3-1.7B` | `fast` | **P0 probe** vs `llama3.2:1b` |
| `Phi-4-mini-instruct` (3.8B) | `balanced` | Math/reasoning upgrade |
| `gemma-3-4b-it` | `balanced` | Already D3-benched (~12–82 tok/s class — check fit) |
| `Qwen2.5-3B-Instruct` | `balanced` (domain) | **P0** untuned baseline vs `qwen2.5-3b-lumen` |
| `Mistral-Small-3.2-7B` Q4 | `quality` | Opt-in quality only |
| `Qwen2.5-Coder-3B` | `code` | **Done** (opt-in) |
| `moondream2` / VL / SD | vision / image | Deferred on 4GB |

- **Status:** in-progress — `scripts/probe_tier_swaps.py` + [PRODUCT-ROADMAP.md](./docs/PRODUCT-ROADMAP.md)
- **Promotion:** deferred (see PROMOTE.md; not this cycle)

### 2026-09-03 — Quality eval only (do NOT add to router)
| Model | Use |
|---|---|
| `Qwen2.5-7B-Instruct` Q4_K_M | Current `quality` baseline |
| `Qwen3-8B` Q4 | Quality probe if it fits |
| `Llama-3.1-8B-Instruct` Q4 | Quality probe |
| `gpt-oss-20b` | AirLLM-only reasoning probe |
| `DeepSeek-R1-Distill-Qwen-7B` | Reasoning quality probe |
| `Qwen3-30B-A3B-Instruct-2507` | MoE probe via AirLLM |
- **Reason:** would tank the +40% mean if added to the hybrid router
- **Status:** proposed

---

### 2026-09-03 — Tier swap probe (P0)
- **Type:** model
- **Script:** `scripts/probe_tier_swaps.py` on reference 1650
- **Results:**
  | Slot | Model | tok/s | Decision |
  |------|-------|-------|----------|
  | fast | `llama3.2:1b` | **96.2** | **keep** |
  | fast candidate | `qwen3:1.7b` | 86.1 | reject for speed (also empty reply on short prompt) |
  | balanced | `lfm-balanced` | 65.2 | keep |
  | domain | `qwen2.5-3b-lumen` | 55.2 | tok/s ≈ stock; **quality smoke next** |
  | domain baseline | `qwen2.5:3b-instruct-q4_K_M` | 55.5 | baseline for S07 delta |
- **Domain quality (production payload):**
  - `qwen2.5-3b-lumen`: correctly describes Lumen as local LLM orchestration / hybrid router
  - stock `qwen2.5:3b-instruct`: does not know the project
  - **Keep domain model** — quality win, not tok/s win
- **Status:** shipped (no default swaps; keep `llama3.2:1b` + `qwen2.5-3b-lumen`)

---

## In progress

### 2026-09-03 — LFM answer quality + opt-in reason tier
- **Type:** capability / model
- **LFM fix:** `visible_response()` strips meta lead + think/boxed; balanced default `num_predict=192`
  - Lab smoke: TCP/apples answers now start with real content (not "The user wants…")
  - Alias recreate: inherit source ChatML TEMPLATE (do not collapse to `{{ .Prompt }}`)
- **Reason tier:** `phi4-mini` via `--tier reason` / `/tier reason`; auto only if `LUMEN_REASON_TIER=1`
  - ~30 tok/s on 1650 — **never** default auto (would tank +40% mean)
- **Status:** shipped (LFM post-process on; reason opt-in only)

### 2026-09-03 — Router v2 A/B behind flag
- **Type:** capability
- **Change:** `route_with_engine()` + `LUMEN_ROUTER=v2` (CLI `--router`, menu, gateway in-process)
- **A/B:** `scripts/ab_router_v2.py --holdout` → eval **12/12** match, holdout **10/10** match
- **Decision:** keep **keyword** as default (v2 is teacher-clone today; no speed delta until logs retrain). Opt-in via env for experimentation.
- **Status:** shipped (flagged; not default)

### 2026-09-03 — Balanced slot probe (newer model versions)
- **Type:** model
- **Script:** `scripts/probe_tier_swaps.py --slot balanced` on reference 1650
- **Results (general TCP/UDP, num_predict=96):**
  | Model | tok/s | VRAM | Notes |
  |-------|-------|------|-------|
  | `lfm-balanced` | **65.7** | 2273 | Fastest; meta/scratchpad style answers |
  | `qwen3:4b` | 27.1 | 2301 | empty `response` unless `think:false` |
  | `phi4-mini` | 29.7 | 2281 | Clean answers; math **correct** (40 apples) |
  | `gemma3:4b-it-qat` | 12.1 | 2431 | Too slow |
- **Decision:** **keep LFM** as default balanced (swap would tank +40% mean).
- **Tune shipped with this probe:**
  - Recreate `lfm-balanced` Modelfile (concise SYSTEM, temp 0.5) via `win-create-lfm-alias.ps1 -Force`
  - Default API `think: false` (`LUMEN_THINK`) — fixes Qwen3 empty replies; LFM still narrates (not Ollama-think-tagged)
  - `visible_response()` strips trailing `</think>` answer when present (menu + gateway)
- **Status:** shipped (no default model swap; LFM stays; quality path = post-process + optional future phi4 opt-in)

### 2026-09-03 — Regression gate re-run (post tooling churn)
- **Type:** capability / gate
- **Result:** `deploy/win-regression.ps1` **ALL PASS** on reference 1650
  - Orchestration mean **69.12** tok/s vs always-3B 48.38 → **+42.9%** (need +40%)
  - Domain smoke: `qwen2.5-3b-lumen` correct; stock 3B still confuses with Laravel
- **Status:** shipped

### 2026-09-03 — `keep_alive` + tier thrash
- **Type:** capability
- **Change:** production payloads set `keep_alive` via `resolve_keep_alive()` / `Resolve-KeepAlive`
  - Default **`10m`** (`LUMEN_KEEP_ALIVE`); `0` unloads; `off` omits (server default)
  - Wired in `lumen_router.ollama_generate_payload` + `deploy/win-router-lib.ps1`
  - Bench: `scripts/bench_tier_thrash.py`
- **Lab (1650, 2026-09-03):**
  | Arm | Cross-tier wall | Same-tier streak wall |
  |-----|-----------------|------------------------|
  | unload each (`0`) | 11.03 s | 9.47 s |
  | keep `10m` | 13.20 s (−19% worse) | **5.46 s (−42%)** |
- **Decision:** keep default **`10m`**. Wins multi-turn same-tier (load≈0 after first). Cross-tier on 4GB still pays full swap; keep_alive does not reduce that thrash.
- **Status:** shipped

### 2026-09-03 — GPU util in benches (`nvidia-smi`)
- **Type:** capability
- **Reason:** Windows Task Manager often shows RAM/CPU spikes and 0% GPU because it graphs the **3D** engine, not CUDA compute. Ollama uses CUDA.
- **Change:** `python3 lumen.py bench` and `python3 lumen.py gpu` sample `utilization.gpu` + VRAM during generate. Portable `deploy/win-gpu-check.ps1` (no hardcoded machine paths).
- **Smoke:** `deploy/win-upgrade-smoke.ps1` includes a 64-token GPU generate.
- **Status:** shipped (CUDA util confirmed on reference 1650: max ~53–94% during generate; Task Manager 3D still misleading)

### 2026-09-03 — Experimental `code` tier (opt-in)
- **Type:** capability
- **Tier:** `code` → `qwen2.5-coder:3b` (Ollama tag; pull before using)
- **Reason:** E07-style coding prompts currently share `balanced` (LFM). A dedicated coder must not change the 12/12 suite unless `LUMEN_CODE_TIER=1`.
- **Gate:** default **off**. `python3 lumen.py route --tier code` always available.
- **Tune (GTX 1650, 2026-09-03):** `scripts/tune_code_tier.py`
  - LFM chat: **65.1 tok/s**, wall **4.6 s**
  - Coder chatlike (temp 0.7): 54.8 tok/s, wall 5.7 s
  - Coder **code_default** (temp 0.1, ctx 2048, batch 512 + concise system): **55.3 tok/s**, wall **1.6 s**
  - Smaller ctx/batch did **not** beat code_default on this prompt; wall win is shorter answers, not higher decode.
- **Presets:** `CODE_DEFAULT_OPTIONS` in `lumen_router.py`; override with `LUMEN_CODE_TEMPERATURE` / `LUMEN_CODE_NUM_CTX` / `LUMEN_CODE_NUM_BATCH`. Gateway uses them for `tier=code`.
- **Decision (2026-09-03):** keep auto-route **off**. Forced `--tier code` / menu `/tier code` use tuned presets. No further knob chasing until a quality regression appears.
- **Status:** shipped (opt-in only; `LUMEN_CODE_TIER` remains unset)

---

## Shipped

### 2026-08-31 — Hybrid router v1
- llama3.2:1b / lfm-balanced / qwen2.5-3b-lumen / qwen2.5-7b-lumen
- +44.7% mean decode tok/s on 12-prompt eval suite
- `win-router-lib.ps1` and `lumen_router.py` in sync
- **Status:** shipped, regression gate active

### 2026-08-31 — Phase D2 (LFM family)
- LFM chosen as `balanced` default
- Gemma 4 / Nemotron benched and rejected for 4 GB
- **Status:** shipped

### 2026-08-31 — llama.cpp vs Ollama bench scripts
- `scripts/bench_backends.py`, `deploy/win-bench-llamacpp-vs-ollama.ps1`
- **Status:** shipped

---

## Rolled back

### S08 — 3B re-train max_length 96
- Train PASS, domain quality regressed
- Rolled back to S07 (`qwen2.5-3b-lumen`)
- **Status:** rolled back 2026-08-31

---

## Convention for new entries

1. Add to **Open proposals** with today's date and reason.
2. Move to **In progress** when code/config starts changing.
3. Move to **Shipped** with bench deltas once `win-regression.ps1` PASSES.
4. Move to **Rolled back** if quality or perf regresses; keep the entry so we don't re-litigate.
5. Never delete entries — `UPGRADES.md` is a changelog, not a feature list.
