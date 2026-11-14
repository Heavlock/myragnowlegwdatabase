#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PGCODEKEEPER_RUNNER="${SCRIPT_DIR}/scripts/pgcodekeeper.sh"
DB_DSN="${MYRAG_DB_DSN:-jdbc:postgresql://localhost:6432/rag?user=rag&password=rag}"

"${PGCODEKEEPER_RUNNER}" \
  -s "${SCHEMA_DIR:-${SCRIPT_DIR}/sql/project}" \
  -t "${DB_DSN}" \
  -X \
  -P \
  --ignore-column-order \
  -r
