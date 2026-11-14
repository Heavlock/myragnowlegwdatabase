#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PGCODEKEEPER_RUNNER="${SCRIPT_DIR}/scripts/pgcodekeeper.sh"
DB_DSN="${MYRAG_DB_DSN:-jdbc:postgresql://localhost:6432/rag?user=rag&password=rag}"
OUTPUT_FILE="${MIGRATION_OUTPUT:-${SCRIPT_DIR}/sql/migrations/myrag.sql}"

mkdir -p "$(dirname "${OUTPUT_FILE}")"

"${PGCODEKEEPER_RUNNER}" \
  -s "${SCHEMA_DIR:-${SCRIPT_DIR}/sql/project}" \
  -t "${DB_DSN}" \
  -o "${OUTPUT_FILE}" \
  -X \
  -P \
  --ignore-column-order

echo "Saved migration diff to ${OUTPUT_FILE}"
