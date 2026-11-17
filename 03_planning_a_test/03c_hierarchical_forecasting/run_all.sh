#!/usr/bin/env bash
# End to end: tests, the three pre-specified backtests, then tables and memo tables.
# The figure is drawn from reports/tables/ by figures/make_study_figures.py at the repository root.
# Needs the Zillow files downloaded by hand into data_external/zillow/v1_20261109/ (see README).
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python}
mkdir -p tmp/logs
$PY -m pytest tests -q
for spec in "inventory ets" "inventory arima" "new_listings ets"; do
  set -- $spec
  echo "== backtest $1 / $2"
  $PY scripts/run_backtest.py --target "$1" --base "$2" --jobs "${JOBS:-8}" > "tmp/logs/run_$1_$2.log" 2>&1
  grep -h "runtime_secs" "tmp/logs/run_$1_$2.log" || true
done
$PY scripts/xcheck_nixtla_real.py > tmp/logs/xcheck.log 2>&1
$PY scripts/make_report.py
$PY scripts/check_memo.py
