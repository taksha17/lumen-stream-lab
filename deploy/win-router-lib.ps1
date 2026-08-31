# Shared routing logic for win-route.ps1 and win-router-eval.ps1
# Speed-first quality; hybrid balanced (LFM general / qwen domain).

$script:RouterModels = @{
    fast            = "llama3.2:1b"
    balanced        = "lfm-balanced"      # alias -> LFM 2.5-2.6B Q4 (~65 tok/s)
    balanced_domain = "qwen2.5-3b-lumen"  # ~54 tok/s Lumen domain
    quality         = "qwen2.5-7b-lumen"
}

$script:QualityMinWords = 50
$script:QualityKeywordMinWords = 35

function Get-DomainSystemPrompt {
    $path = Join-Path (Split-Path $PSScriptRoot -Parent) "data\domain-system-prompt.txt"
    if (Test-Path $path) {
        return (Get-Content $path -Raw).Trim()
    }
    return "You are the domain assistant for Lumen Stream Lab, an open-source local LLM orchestration research project. It is NOT Laravel Lumen, Liquid AI, telecom, or video streaming. Answer about this ML orchestration project only."
}

function Test-IsDomainModel([string]$model) {
    return $model -eq $script:RouterModels.balanced_domain
}

function New-OllamaGeneratePayload([string]$model, [string]$prompt, [hashtable]$options) {
    $payload = [ordered]@{
        model  = $model
        prompt = $prompt
        stream = $false
        options = $options
    }
    if (Test-IsDomainModel $model) {
        $payload.system = Get-DomainSystemPrompt
    }
    return $payload
}

function Test-RouterKeywordMatch([string]$text, [string[]]$keywords) {
    $lower = $text.ToLower()
    foreach ($kw in $keywords) {
        if ($lower -like "*$kw*") { return $true }
    }
    return $false
}

function Test-LumenDomainPrompt([string]$text) {
    # Strict: project-specific phrases only (avoid bench/troubleshooting false positives)
    $domainKeywords = @(
        'lumen stream lab',
        'laravel lumen',
        'stream_layers',
        'soup train',
        'soup chat',
        '1b vs 3b',
        '3b vs 7b',
        'lumen stream'
    )
    if (Test-RouterKeywordMatch $text $domainKeywords) { return $true }

    $lower = $text.ToLower()
    if ($lower -like '*lumen*' -and (
            $lower -like '*route*' -or $lower -like '*router*' -or
            $lower -like '*stream lab*' -or $lower -like '*fine-tune*'
        )) { return $true }

    if ($lower -like '*layer streaming*' -and (
            $lower -like '*soup*' -or $lower -like '*lumen*'
        )) { return $true }

    return $false
}

function Get-BalancedModel([string]$text) {
    if (Test-LumenDomainPrompt $text) {
        return @{
            model  = $script:RouterModels.balanced_domain
            reason = "balanced/domain (Lumen keywords)"
        }
    }
    return @{
        model  = $script:RouterModels.balanced
        reason = "balanced/general (LFM speed)"
    }
}

function Test-QualityRoute([string]$text, [int]$words) {
    $qualityKeywords = @(
        'detailed', 'comprehensive', 'thorough', 'in-depth', 'in depth',
        'essay', 'write a story', 'creative', 'code review', 'design a system',
        'best answer', 'high quality', 'expert', 'research', 'whitepaper',
        'proofread', 'refactor', 'production-grade'
    )
    if ($words -gt $script:QualityMinWords) { return $true }
    if ($words -gt $script:QualityKeywordMinWords -and (Test-RouterKeywordMatch $text $qualityKeywords)) {
        return $true
    }
    return $false
}

function Get-RouteDecision([string]$text, [string]$tierPref) {
    if ($tierPref -ne "auto") {
        if ($tierPref -eq "balanced") {
            $b = Get-BalancedModel $text
            return @{ tier = "balanced"; model = $b.model; reason = "forced tier=balanced ($($b.reason))" }
        }
        return @{ tier = $tierPref; model = $script:RouterModels[$tierPref]; reason = "forced tier=$tierPref" }
    }

    $words = ($text -split '\s+').Count
    $complexKeywords = @(
        'explain', 'analyze', 'compare', 'describe', 'why', 'how does',
        'algorithm', 'architecture', 'implement', 'debug', 'step by step',
        'pros and cons', 'summarize', 'difference between', 'route', 'routing',
        'lumen', 'model tier', 'when should', 'streaming', 'fine-tune'
    )
    $simplePatterns = @(
        '^\s*what is \d+\s*[\+\-\*\/]\s*\d+',
        '^\s*\d+\s*[\+\-\*\/]\s*\d+\s*\??\s*$',
        '^(hi|hello|hey)\b',
        '^(yes|no|thanks|thank you)\b',
        '^\s*capital of\b'
    )

    foreach ($pat in $simplePatterns) {
        if ($text -match $pat) {
            return @{ tier = "fast"; model = $script:RouterModels.fast; reason = "simple pattern match" }
        }
    }

    if (Test-QualityRoute $text $words) {
        return @{ tier = "quality"; model = $script:RouterModels.quality; reason = "quality/long ($words words)" }
    }

    if ($words -le 12 -and -not (Test-RouterKeywordMatch $text $complexKeywords)) {
        return @{ tier = "fast"; model = $script:RouterModels.fast; reason = "short/simple ($words words)" }
    }

    if (Test-RouterKeywordMatch $text $complexKeywords -or $words -gt 20) {
        $b = Get-BalancedModel $text
        return @{ tier = "balanced"; model = $b.model; reason = $b.reason }
    }

    $b = Get-BalancedModel $text
    return @{ tier = "balanced"; model = $b.model; reason = "default $($b.reason)" }
}
