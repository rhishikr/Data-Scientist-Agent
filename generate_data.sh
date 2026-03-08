#!/usr/bin/env bash
# Generate a fresh set of synthetic retail data from scratch.
# This replaces ALL existing CSVs in backend/data/raw/ with new baseline data.
#
# Datasets generated (12 files):
#   customers.csv, products.csv, marketing.csv, sessions.csv,
#   inventory.csv, events.csv, web_analytics.csv, transactions.csv,
#   transactions_with_session.csv, payments.csv, campaign_performance.csv,
#   funnel_summary.csv
#
# Usage:
#   bash generate_data.sh
#
# Note: This script takes no arguments. To simulate incremental updates
#       on top of existing data, use update_data.sh instead.
cd "$(dirname "$0")/backend" || exit 1

if [ -d "venv" ]; then
  source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
fi

python scripts/generate_synthetic_data.py
