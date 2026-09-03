# Promote Lumen (DEFERRED)

**Paused.** Product scaling/tuning is the priority — see [PRODUCT-ROADMAP.md](./PRODUCT-ROADMAP.md).

Paste-ready Reddit/HN drafts stay below for later. Do **not** spend cycles here until the next product gate ships. Never paste tokens, SSH hosts, or local usernames.

<details>
<summary>Parked drafts (expand later)</summary>

## LocalLLaMA — earn karma (no repo links)

**1 — 4GB / laptop GPU**

> On a 1650 4GB, always using llama3.2:3b sat around 48 tok/s for every prompt. Routing arithmetic to 1B (~99) and keeping 7B opt-in (~10) was what moved the mean.

**2 — Ollama vs llama.cpp**

> Same llama3.2:3b GGUF on that 1650: Ollama ~49 tok/s, llama.cpp ~16. Re-bench per GPU.

**3 — hybrid vs one model**

> Hybrid (1B + balanced + domain 3B) beat picking one winner on 4GB.

## LocalLLaMA — post (after karma)

Title: Hybrid routing on a 4GB 1650: +40% vs always-3B (Ollama, fully local)

Repo: https://github.com/taksha17/lumen-stream-lab · issue #1 for hardware profiles

## Show HN (later)

`Show HN: Lumen – route local LLMs by prompt, +40% on 4GB VRAM`

</details>
