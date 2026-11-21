#!/usr/bin/env bash
set -euo pipefail
for u in "https://alfabank.ru/" "https://www.avito.ru/"; do
  echo "=== $u ==="
  id=$(curl -s -X POST http://127.0.0.1:8001/api/scans \
    -H "Content-Type: application/json" \
    -d "{\"target_url\":\"$u\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  sleep 3
  curl -s "http://127.0.0.1:8001/api/scans/$id" | python3 -m json.tool
  curl -s "http://127.0.0.1:8001/api/scans/$id/findings" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d),'findings'); [print('-',x['title']) for x in d[:5]]"
done