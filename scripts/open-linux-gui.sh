#!/usr/bin/env bash
set -euo pipefail

URL="http://localhost:8080"

for _ in $(seq 1 30); do
  if command -v curl >/dev/null 2>&1 && curl -fsS "$URL/api/status" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 &
elif command -v sensible-browser >/dev/null 2>&1; then
  sensible-browser "$URL" >/dev/null 2>&1 &
else
  echo "No browser opener found. Open $URL manually."
fi
