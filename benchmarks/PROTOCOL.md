# Benchmark Protocol

Fair measurement rules for the **+40% speed goal**.

## What we measure

| Metric | Definition |
|--------|------------|
| **Decode tok/s** | Output tokens per second during steady generation (primary metric) |
| **TTFT** | Milliseconds from prompt submit to first output token |
| **Peak VRAM** | Max GPU memory during run |

## Fixed conditions

1. **Same model** — e.g. `mistral:7b-instruct-q4_0`, not a different size for "optimized"
2. **Same quant** — Q4_K_M vs Q4_0 must match across runs
3. **batch_size = 1** — single user chat
4. **temperature = 0** — reproducible (or fixed seed)
5. **max_new_tokens = 128** — long enough to exit prefill noise
6. **Power plugged in** — laptop on AC, performance mode if available
7. **Close Chrome, etc.** — free RAM and VRAM

## Warmup

- **2 warmup runs** — discard (loads weights, fills cache)
- **5 measured runs** — report **median** decode tok/s

## Cold vs warm

| Type | Definition | When to use |
|------|------------|-------------|
| **Cold** | First run after reboot / cache clear | Worst case |
| **Warm** | After 2+ warmup runs | **Primary metric for +40% claim** |

## Prompt suite

Use `benchmarks/prompts.txt` — fixed lines, mixed lengths:

- Short (10 tokens)
- Medium (50 tokens)
- Long prefill (200+ tokens)

Report **median across all prompts**, not best single prompt.

## How to read tok/s per backend

### Ollama

```bash
ollama run mistral:7b-instruct-q4_0 "Explain quantum computing in simple terms." --verbose 2>&1 | grep -i eval
```

Look for `eval rate` or tokens/s in verbose output.

### llama.cpp

```bash
llama-cli -m model.gguf -p "Explain quantum computing." -n 128 --temp 0 -ngl 99 2>&1 | grep "tokens per second"
```

### AirLLM

```python
model = AutoModel.from_pretrained(..., profiling_mode=True)
# Check printed timing breakdown
```

### Colibri

Watch stats line per turn for tok/s in chat output or logs.

## Baseline selection

**Baseline = best median decode tok/s among resident backends** (Ollama, llama.cpp, Soup serve) without Lumen optimizations.

Do **not** use AirLLM layer streaming as baseline for a model that fits in VRAM — it's the wrong tool for speed.

## Pass / fail for +40%

```
improvement = (optimized_median - baseline_median) / baseline_median

PASS if improvement >= 0.40
```

Document in `docs/RESULTS.md` with run IDs.

## Anti-patterns (invalid comparisons)

| Invalid | Why |
|---------|-----|
| 7B baseline → 3B optimized | Different model |
| FP16 baseline → Q4 optimized | Different quant |
| Cold baseline → warm optimized | Unfair |
| 50 token gen baseline → 10 token optimized | Prefill dominates short runs |
| AirLLM stream baseline → Ollama optimized | Wrong baseline tool |
