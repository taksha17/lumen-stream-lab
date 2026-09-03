---
license: apache-2.0
base_model: Qwen/Qwen2.5-3B-Instruct
tags:
  - lumen-stream-lab
  - gguf
  - ollama
  - qwen2.5
---

# qwen2.5-3b-lumen (S07 domain fine-tune)

Domain tier for **[Lumen Stream Lab](https://github.com/taksha17/lumen-stream-lab)** — a hybrid router that sends Lumen/Soup/routing questions here instead of a generic 3B.

- **Repo:** https://github.com/taksha17/lumen-stream-lab
- **Walkthrough:** [60s video](https://github.com/taksha17/lumen-stream-lab#walkthrough-60s)
- **Sister model (quality, slower on 4GB):** [qwen2.5-7b-lumen](https://huggingface.co/takshathosani17/qwen2.5-7b-lumen)
- **Hardware profiles wanted:** [issue #1](https://github.com/taksha17/lumen-stream-lab/issues/1)

Reference lab (GTX 1650 4GB): domain ~56 tok/s; hybrid orchestration mean **68.10** vs always-3B **48.38** (+40.8%).

## Ollama

```bash
hf download takshathosani17/qwen2.5-3b-lumen --local-dir ./qwen-3b-lumen
cd qwen-3b-lumen
ollama create qwen2.5-3b-lumen -f Modelfile
```

Modelfile:

```
FROM ./qwen2.5-3b-lumen-s07.q4_k_m.gguf
PARAMETER temperature 0.7
```

Trained with Soup `config/soup/soup-3b-stream-s07.yaml` on the reference lab.
