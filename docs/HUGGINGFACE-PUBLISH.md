# Publishing domain models to Hugging Face

Share `qwen2.5-3b-lumen` so contributors can download GGUF without running Soup training.

**Live model:** [takshathosani17/qwen2.5-3b-lumen](https://huggingface.co/takshathosani17/qwen2.5-3b-lumen)

## Prerequisites

1. GGUF on reference lab: `D:\lumen-stream-lab\exports\qwen2.5-3b-lumen-s07.q4_k_m.gguf`  
   (create via `deploy\win-post-s07.ps1` if missing)
2. Hugging Face account + [write token](https://huggingface.co/settings/tokens)
3. `pip install huggingface_hub[cli]`

## One-command publish (Windows reference lab)

```powershell
$env:HF_TOKEN = "hf_..."
powershell -File deploy\win-publish-hf.ps1 -RepoId YOUR_USERNAME/qwen2.5-3b-lumen
```

From Linux (GGUF stays on server; token on your PC):

```bash
export HF_TOKEN=hf_...
chmod +x deploy/publish-hf-remote.sh
./deploy/publish-hf-remote.sh YOUR_USERNAME/qwen2.5-3b-lumen
```

**Note:** Use `hf upload` (not deprecated `huggingface-cli upload`) — the publish script sets UTF-8 env vars to avoid Windows `cp1252` Unicode errors.

Dry run (stage files only):

```powershell
powershell -File deploy\win-publish-hf.ps1 -RepoId YOUR_USERNAME/qwen2.5-3b-lumen -DryRun
```

Uploads:
- `qwen2.5-3b-lumen-s07.q4_k_m.gguf`
- `Modelfile` for Ollama
- `README.md` with license + usage

## After publish — contributor install

```bash
pip install -U "huggingface_hub[cli]"
hf download takshathosani17/qwen2.5-3b-lumen --local-dir ./qwen-lumen
cd qwen-lumen
ollama create qwen2.5-3b-lumen -f Modelfile
```

See also [MODELS.md](./MODELS.md).

## 7B model

Same pattern with `exports\qwen2.5-7b-lumen*.gguf` and `deploy\win-export-7b.ps1`.
