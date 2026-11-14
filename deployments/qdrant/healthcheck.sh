#!/usr/bin/env bash
set -euo pipefail
# The official image has Bash, but no curl/wget. Probe the real readiness URL.
exec 3<>/dev/tcp/127.0.0.1/6333
printf 'GET /readyz HTTP/1.0\r\nHost: localhost\r\n\r\n' >&3
IFS= read -r status <&3
[[ "$status" == *" 200 "* ]]
