#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_FILE="${EMBEDDING_MODEL_FILE:-${PROJECT_ROOT}/models/Qwen3-Embedding-0.6B-Q8_0.gguf}"
MODEL_SHA256=06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439
MODEL_URL=https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/370f27d7550e0def9b39c1f16d3fbaa13aa67728/Qwen3-Embedding-0.6B-Q8_0.gguf

verify() {
  local actual
  actual="$(sha256sum -- "$1")"
  [[ "${actual%% *}" == "$MODEL_SHA256" ]]
}

if [[ -e "$MODEL_FILE" ]]; then
  if [[ -f "$MODEL_FILE" ]] && verify "$MODEL_FILE"; then
    echo "Verified existing Qwen model: $MODEL_FILE"
    exit 0
  fi
  echo "Existing model path is not the expected Qwen Q8_0 file: $MODEL_FILE" >&2
  echo 'Choose another EMBEDDING_MODEL_FILE path or move the existing file before downloading.' >&2
  exit 1
fi

mkdir -p "$(dirname "$MODEL_FILE")"
temporary_file="$(mktemp "${MODEL_FILE}.download.XXXXXX")"
trap 'rm -f -- "$temporary_file"' EXIT
curl --fail --location --retry 3 --output "$temporary_file" "$MODEL_URL"
if ! verify "$temporary_file"; then
  echo 'Downloaded model failed SHA-256 verification; destination was not changed.' >&2
  exit 1
fi
mv -- "$temporary_file" "$MODEL_FILE"
echo "Downloaded and verified Qwen model: $MODEL_FILE"
