#!/usr/bin/env bash
# Simulate a retail dataset update with configurable duration and business scenario.
#
# Usage:
#   bash update_data.sh [--days N] [--scenario SCENARIO]
#
# Options:
#   --days N        Number of days to simulate (default: 7)
#   --scenario S    Business scenario to simulate (default: organic-growth)
#
# Available scenarios:
#   organic-growth     Steady, natural business growth (default)
#   profit             Business thriving: high conversions, low returns, strong margins
#   loss               Declining performance: low conversions, high returns
#   seasonal-spike     Temporary surge in demand (e.g. holiday season)
#   stockout-crisis    Inventory shortages impacting sales
#   marketing-blitz    Heavy marketing spend driving traffic
#   churn-wave         Increased customer churn
#   new-product-launch New product introduction with early adoption patterns
#
# Examples:
#   bash update_data.sh                              # 7-day organic growth
#   bash update_data.sh --days 14 --scenario profit  # 14-day profit scenario
#   bash update_data.sh --scenario stockout-crisis   # 7-day stockout crisis
cd "$(dirname "$0")/backend" || exit 1

if [ -d "venv" ]; then
  source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
fi

python scripts/simulate_update.py "$@"
