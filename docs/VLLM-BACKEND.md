# vLLM backend (optional)

For contributors with **8GB+ VRAM** where [vLLM](https://github.com/vllm-project/vllm) beats Ollama throughput.

## Setup

```bash
pip install vllm
vllm serve Qwen/Qwen2.5-3B-Instruct --port 8000
```

## Lumen config

Copy `lumen.yaml.example` → `lumen.yaml`:

```yaml
routing:
  prefer: vllm   # experimental — gateway checks backends.vllm

backends:
  ollama:
    url: http://127.0.0.1:11434
  vllm:
    enabled: true
    url: http://127.0.0.1:8000
    model: Qwen/Qwen2.5-3B-Instruct
```

## Gateway

`scripts/backends/vllm.py` calls vLLM's OpenAI-compatible `/v1/chat/completions`.

Health check: `GET http://127.0.0.1:8000/health`

## Reference lab note

GTX 1650 4GB — **Ollama remains default** (~49 tok/s vs llama.cpp 16 tok/s). vLLM is documented for contributor hardware profiles, not the 4GB CI rig.

Bench on your machine and PR `hardware/<your-profile>.json`.
