#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
profile="${1:-postgres}"
case "$profile" in postgres|qdrant) ;; *) echo 'Usage: docker_compose_smoke_test.sh [postgres|qdrant]' >&2; exit 2;; esac
compute="${COMPUTE_MODE:-cpu}"
case "$compute" in cpu|gpu) ;; *) echo 'COMPUTE_MODE must be cpu or gpu' >&2; exit 2;; esac
project="myrag-smoke-${profile}-${compute}-$$"
compose=(docker compose -f docker-compose.yml)
if [[ "$compute" == gpu ]]; then compose+=(-f docker-compose.gpu.yml); fi
compose+=(-p "$project" --profile "$profile")
report="reports/profiles/${profile}-${compute}.json"
mkdir -p reports/profiles
# Choose unused loopback ports. Each run owns its project and disposable volumes.
read -r POSTGRES_PORT POSTGRES_APP_PORT POSTGRES_MCP_PORT QDRANT_PORT QDRANT_APP_PORT QDRANT_MCP_PORT < <(python3 - <<'PY'
import socket
sockets=[]
for _ in range(6):
 s=socket.socket();s.bind(('127.0.0.1',0));sockets.append(s)
print(' '.join(str(s.getsockname()[1]) for s in sockets))
for s in sockets:s.close()
PY
)
export POSTGRES_PORT POSTGRES_APP_PORT POSTGRES_MCP_PORT QDRANT_PORT QDRANT_APP_PORT QDRANT_MCP_PORT
cleanup() {
  local result=$?
  if [[ $result -ne 0 ]]; then
    "${compose[@]}" logs --tail 60 > "reports/profiles/${profile}-${compute}-failure.log" 2>&1 || true
  else
    rm -f "reports/profiles/${profile}-${compute}-failure.log"
  fi
  "${compose[@]}" down --volumes --remove-orphans --rmi local >/dev/null 2>&1 || true
  return "$result"
}
trap cleanup EXIT
if [[ "$profile" == postgres ]]; then
  app=app; mcp=mcp; app_port=$POSTGRES_APP_PORT; mcp_port=$POSTGRES_MCP_PORT
else
  app=app-qdrant; mcp=mcp-qdrant; app_port=$QDRANT_APP_PORT; mcp_port=$QDRANT_MCP_PORT
fi
"${compose[@]}" up -d --build --wait
# Prove that the selected profile did not start the other database.
services="$("${compose[@]}" ps --services --status running)"
if [[ "$profile" == qdrant ]] && [[ "$services" == *postgres* ]]; then echo 'Qdrant profile unexpectedly started PostgreSQL' >&2; exit 1; fi
if [[ "$profile" == postgres ]] && [[ "$services" == *qdrant* ]]; then echo 'Postgres profile unexpectedly started Qdrant' >&2; exit 1; fi
wait_http() {
  for _ in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:${app_port}/" >/dev/null; then return; fi
    sleep 1
  done
  echo 'Application did not become ready' >&2; return 1
}
wait_http
python3 scripts/profile_smoke.py --base-url "http://127.0.0.1:${app_port}" --mcp-url "http://127.0.0.1:${mcp_port}/mcp" --backend "$profile" --report "$report"
"${compose[@]}" restart "$profile"
"${compose[@]}" up -d --wait "$profile"
"${compose[@]}" restart "$app" "$mcp"
wait_http
python3 scripts/profile_smoke.py --base-url "http://127.0.0.1:${app_port}" --mcp-url "http://127.0.0.1:${mcp_port}/mcp" --backend "$profile" --report "$report" --verify-persistence
printf 'Profile %s passed; saved %s\n' "$profile" "$report"
