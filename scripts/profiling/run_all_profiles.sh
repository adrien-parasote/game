#!/usr/bin/env bash
# --------------------------------------------------------------
# run_all_profiles.sh – execute CPU and memory profiling for the game
# --------------------------------------------------------------
# Usage:
#   ./scripts/profiling/run_all_profiles.sh [duration-seconds]
# If no duration is supplied, defaults to 300 s (5 minutes).
# --------------------------------------------------------------

set -euo pipefail   # fail fast on errors, treat unset vars as errors

# ----- Parameters ------------------------------------------------
DUR=${1:-300}               # profiling duration (seconds)

echo "=== Profiling session start ==="
echo "Duration: $DUR seconds"
echo "Timestamp: $(date +"%Y-%m-%d %H:%M:%S")"
echo ""

# ----- 1️⃣ CPU profiling -----------------------------------------
echo "Running CPU profiling (cProfile)…"
./scripts/profiling/cpu_profile.sh "$DUR"
echo "→ CPU top‑functions CSV generated at: scripts/profiling/cpu_top_functions.csv"
echo ""

# ----- 2️⃣ Memory profiling --------------------------------------
echo "Running memory profiling (mprof)…"
# Start mprof in background, let it run for the requested duration, then stop.
mprof run --python src/main.py &
MPROF_PID=$!
# Give the game a moment to start
sleep 2
# Let it run for the requested duration
sleep "$DUR"
# Stop mprof (SIGINT) to finalize the report
kill -INT "$MPROF_PID" || true
wait "$MPROF_PID" || true

# Convert the raw data to CSV and PNG
mprof plot --output scripts/profiling/memory_plot.png
mprof dump -f scripts/profiling/memory_raw.csv

echo "→ Memory plot PNG generated at: scripts/profiling/memory_plot.png"
echo "→ Memory raw CSV generated at: scripts/profiling/memory_raw.csv"
echo ""

# ----- Summary ---------------------------------------------------
echo "=== Profiling session completed ==="
echo "Files generated:"
echo " • scripts/profiling/cpu_top_functions.csv"
echo " • scripts/profiling/memory_plot.png"
echo " • scripts/profiling/memory_raw.csv"
echo ""
echo "You can now zip the three artefacts and share them:"
echo "   zip profiling_results.zip \\"
echo "       scripts/profiling/cpu_top_functions.csv \\"
echo "       scripts/profiling/memory_plot.png \\"
echo "       scripts/profiling/memory_raw.csv"
echo ""
