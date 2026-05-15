#!/usr/bin/env bash
set -euo pipefail

# Usage: ./cpu_profile.sh [duration-seconds] (default 300)
DUR=${1:-300}

echo "=== CPU profiling for $DUR seconds ==="

# Ensure python3 is available
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found in PATH." >&2
  exit 1
fi

# Temporary file for binary cProfile stats
TMP_STATS=$(mktemp /tmp/cpu_profile.XXXXXX)
export TMP_STATS

# Run the game under cProfile for the requested duration using timeout
# The timeout will send SIGTERM after $DUR seconds, allowing cProfile to write stats.
timeout "$DUR" python3 - <<'PY'
import os, cProfile
stats_path = os.getenv('TMP_STATS')
# Execute the game's entry point under profiling
cProfile.run('import src.main; src.main.main()', stats_path, sort='cumulative')
PY

# Convert top 20 functions to CSV for analysis
CSV=scripts/profiling/cpu_top_functions.csv
python3 - <<'PY' "$TMP_STATS" "$CSV"
import sys, pstats, csv
stats_path, csv_path = sys.argv[1], sys.argv[2]
ps = pstats.Stats(stats_path)
ps.sort_stats('cumulative')
with open(csv_path, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['func','calls','total_time','cumulative_time','filename:lineno'])
    for func, data in list(ps.stats.items())[:20]:
        filename, lineno, name = func
        w.writerow([name, data[0], f"{data[2]:.6f}", f"{data[3]:.6f}", f"{filename}:{lineno}"])
PY

# Clean up temporary stats file
rm -f "$TMP_STATS"
