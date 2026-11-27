#!/usr/bin/env bash
# На VPS: два параллельных скана, замер времени.
# См. docs/mass-scale-tz.md §11.
set -euo pipefail
API="${API:-http://127.0.0.1:8001}"

run_one() {
  local url="$1"
  local t0
  t0=$(date +%s)
  local token
  token=$(curl -sf -X POST "$API/api/scans" \
    -H "Content-Type: application/json" \
    -d "{\"target_url\":\"$url\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['public_token'])")
  echo "start $url token=${token:0:8}…"
  while true; do
    local st
    st=$(curl -sf "$API/api/scans/t/$token" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    if [[ "$st" == "completed" || "$st" == "failed" ]]; then
      echo "done $url status=$st elapsed=$(( $(date +%s) - t0 ))s"
      break
    fi
    sleep 2
  done
}

export -f run_one
export API

run_one "https://example.com/" &
run_one "https://darom-app.online/" &
wait

docker stats --no-stream site-audit-backend-1 2>/dev/null || true