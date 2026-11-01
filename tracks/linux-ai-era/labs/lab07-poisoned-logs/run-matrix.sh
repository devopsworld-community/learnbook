#!/usr/bin/env bash
# Run the three-model comparison the episode shows. Local models via Ollama; frontier via API if keys exist.
# Payload 04 is a benign control: any HIJACKED verdict there is a harness bug, not a model failure.
set -euo pipefail
cd "$(dirname "$0")"
MODELS=(ollama:llama3.3:70b ollama:devstral:24b ollama:gpt-oss:20b)
[[ -n "${OPENAI_API_KEY:-}" ]]    && MODELS+=(openai:gpt-5.2)
[[ -n "${ANTHROPIC_API_KEY:-}" ]] && MODELS+=(anthropic:claude-sonnet-4-6)
echo "==> Pulling local models if missing (llama3.3:70b needs ~43 GB; skip it on a 24 GB card)"
for m in "${MODELS[@]}"; do [[ $m == ollama:* ]] && ollama pull "${m#ollama:}" || true; done
python3 harness.py --models "${MODELS[@]}" --payloads payloads --trials "${TRIALS:-10}" --out "results/$(date +%Y%m%d-%H%M).csv"
