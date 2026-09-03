# Promote Lumen (no secrets)

HN and r/LocalLLaMA both need a little karma first. Use this checklist. **Do not paste tokens, SSH hosts, or Windows usernames.**

## Status

| Channel | Barrier | Action |
|---------|---------|--------|
| GitHub | none | Topics + [issue #1](https://github.com/taksha17/lumen-stream-lab/issues/1) live |
| Hugging Face | none | 3B/7B cards updated |
| r/LocalLLaMA | ~5 karma | Comment first (below), then post |
| Show HN | new-account throttle | Comment as a person for 2–4 weeks, then one Show HN |

## Code tier policy (locked)

- Default hybrid: **do not** set `LUMEN_CODE_TIER=1`
- When you want code: `python3 lumen.py route --tier code` or menu `/tier code`
- Tuned presets stay on that path; auto-route stays off so +40% mean holds

## LocalLLaMA — earn karma (no repo links)

Paste one per thread:

**1 — 4GB / laptop GPU**

> On a 1650 4GB, always using llama3.2:3b sat around 48 tok/s for every prompt. Routing arithmetic to 1B (~99) and keeping 7B opt-in (~10) was what moved the mean. Treating 7B as the default on that card just tanks throughput.

**2 — Ollama vs llama.cpp**

> Same llama3.2:3b GGUF on that 1650: Ollama ~49 tok/s, llama.cpp ~16. So a backend swap is not automatically a win. Worth re-benching per GPU instead of assuming llama.cpp is faster.

**3 — which small model**

> 1B is fine for short/simple. Domain questions still hallucinated on stock 1B/3B for us until a small fine-tune + a system prompt. Hybrid (1B + balanced + domain 3B) beat picking one winner.

**4 — VRAM**

> 4GB: 1B and 3B resident are usable; 7B Q4 runs but ~10 tok/s so it should not be the auto route. Training 7B needed stream_layers and max_length 64.

**5 — “just use one 8B”**

> If the box can hold 8B comfortably, that is simpler. The 4GB case is different: one mid-size model for everything is the slow path. Per-prompt size is the cheap lever when you cannot buy VRAM.

## LocalLLaMA — post (after ~5 karma)

**Title:** Hybrid routing on a 4GB 1650: +40% vs always-3B (Ollama, fully local)

**Body:**

```
Most local stacks pick one model and live with it. On a GTX 1650 4GB, always llama3.2:3b sits at ~48 tok/s for everything.

Lumen Stream Lab is a thin router in front of Ollama: each prompt gets a JSON plan (tier, model, reason) before generate.

Reference lab (Ollama 0.33.2, num_predict=128):
- always 3B: 48.38 tok/s
- hybrid auto-route (12 prompts): 68.10 tok/s (+40.8%)
- fast 1B ~99 · LFM ~64 · domain 3B ~56 · 7B quality ~10 (opt-in)
- router eval 12/12

Not claiming frontier quality. Code tier is opt-in (coder is slower than LFM on this card). Offline, no API keys.

Repo: https://github.com/taksha17/lumen-stream-lab
./scripts/demo.sh
Domain GGUFs on HF: qwen2.5-3b-lumen / qwen2.5-7b-lumen
Hardware profiles: https://github.com/taksha17/lumen-stream-lab/issues/1
```

## Show HN (later)

Title: `Show HN: Lumen – route local LLMs by prompt, +40% on 4GB VRAM`  
Link the GitHub repo. Stay in the thread. No vote rings. See [showhn.html](https://news.ycombinator.com/showhn.html).
