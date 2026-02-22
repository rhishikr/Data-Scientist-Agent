#!/usr/bin/env bash
# Generate fresh synthetic retail data in data/raw/
cd "$(dirname "$0")/backend" || exit 1

if [ -d "venv" ]; then
  source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
fi

python scripts/generate_synthetic_data.py
