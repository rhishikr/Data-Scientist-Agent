#!/usr/bin/env bash
# Simulate a dataset update (default 7 days, pass --days N to customize)
cd "$(dirname "$0")/backend" || exit 1

if [ -d "venv" ]; then
  source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
fi

python scripts/simulate_update.py "$@"
