---
license: apache-2.0
base_model: Qwen/Qwen2.5-7B-Instruct
tags:
  - lumen-stream-lab
  - gguf
  - ollama
  - qwen2.5
---

# qwen2.5-7b-lumen (S06 quality tier)

**Opt-in quality tier** for **[Lumen Stream Lab](https://github.com/taksha17/lumen-stream-lab)**. On 4GB VRAM this runs ~10 tok/s — do **not** use it as the default for every prompt. The router keeps it for long / high-quality requests.

- **Repo:** https://github.com/taksha17/lumen-stream-lab
- **Domain (default balanced for Lumen keywords):** [qwen2.5-3b-lumen](https://huggingface.co/takshathosani17/qwen2.5-3b-lumen)
- **Walkthrough:** [60s video](https://github.com/taksha17/lumen-stream-lab#walkthrough-60s)
- **Hardware profiles wanted:** [issue #1](https://github.com/taksha17/lumen-stream-lab/issues/1)

Artifact: `qwen2.5-7b-lumen-s06.q4_k_m.gguf` (~4.7 GB). Ignore any leftover 3B filename if present in this repo.

## Ollama

```bash
hf download takshathosani17/qwen2.5-7b-lumen --local-dir ./qwen-7b-lumen
cd qwen-7b-lumen
# use the 7B GGUF in Modelfile
ollama create qwen2.5-7b-lumen -f Modelfile
```

Modelfile:

```
FROM ./qwen2.5-7b-lumen-s06.q4_k_m.gguf
PARAMETER temperature 0.7
```

Trained with Soup `config/soup/soup-7b-stream-s06.yaml` on the GTX 1650 reference lab.
