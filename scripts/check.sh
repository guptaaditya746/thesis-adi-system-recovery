#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m compileall -q backend/app backend/tests
(cd backend && PYTHONPATH=. pytest -q)
echo "Backend source checks passed."
