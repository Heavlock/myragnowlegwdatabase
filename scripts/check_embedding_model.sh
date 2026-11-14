#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_FILE="${EMBEDDING_MODEL_FILE:-${PROJECT_ROOT}/models/Qwen3-Embedding-0.6B-Q8_0.gguf}"

if [[ -f "${MODEL_FILE}" ]]; then
  echo "Embedding model found at ${MODEL_FILE}"
  exit 0
fi

echo "Embedding model not found: ${MODEL_FILE}" >&2
echo "Set EMBEDDING_MODEL_FILE to the absolute path of the selected embedding GGUF file" >&2
exit 1
