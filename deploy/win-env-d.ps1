# Source this before any Soup/Ollama/HF work on the server
# . D:\lumen-stream-lab\deploy\win-env-d.ps1

$LabRoot = "D:\lumen-stream-lab"
$env:HF_HOME = "$LabRoot\cache\huggingface"
$env:HUGGINGFACE_HUB_CACHE = "$LabRoot\cache\huggingface\hub"
$env:TRANSFORMERS_CACHE = "$LabRoot\cache\huggingface"
$env:SOUP_LAYER_STREAM_CACHE_DIR = "$LabRoot\cache\soup-layer-stream"
$env:OLLAMA_MODELS = "D:\ollama\models"
$env:LUMEN_LAB_ROOT = $LabRoot
