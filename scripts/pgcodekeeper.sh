#!/usr/bin/env bash
set -euo pipefail
cli="${PGCODEKEEPER_CLI:-pgcodekeeper-cli.sh}"
if ! command -v "$cli" >/dev/null 2>&1; then
  echo 'pgCodeKeeper CLI is required. Install it with Java 21+ and set PGCODEKEEPER_CLI to its executable path.' >&2
  exit 127
fi
exec "$cli" "$@"
