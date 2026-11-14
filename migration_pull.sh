#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PGCODEKEEPER_RUNNER="${SCRIPT_DIR}/scripts/pgcodekeeper.sh"
DB_DSN="${MYRAG_DB_DSN:-jdbc:postgresql://localhost:6432/rag?user=rag&password=rag}"
OUTPUT_DIR="${SCHEMA_DIR:-${SCRIPT_DIR}/sql/project}"

mkdir -p "${OUTPUT_DIR}"

"${PGCODEKEEPER_RUNNER}" \
  --mode PARSE \
  -o "${OUTPUT_DIR}" \
  --update-project \
  -P \
  "${DB_DSN}"

echo "Saved database schema into ${OUTPUT_DIR}"
