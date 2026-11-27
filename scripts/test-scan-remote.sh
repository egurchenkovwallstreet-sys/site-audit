#!/usr/bin/env bash
set -euo pipefail
for u in "https://alfabank.ru/" "https://www.avito.ru/"; do
  echo "=== $u ==="
  create_json=$(curl -s -X POST http://127.0.0.1:8001/api/scans \
    -H "Content-Type: application/json" \
    -d "{\"target_url\":\"$u\"}")
  token=$(echo "$create_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['public_token'])")
  sleep 3
  curl -s "http://127.0.0.1:8001/api/scans/t/$token" | python3 -m json.tool
  curl -s "http://127.0.0.1:8001/api/scans/t/$token/findings" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d),'findings'); [print('-',x['title']) for x in d[:5]]"
done