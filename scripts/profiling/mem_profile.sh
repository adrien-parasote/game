#!/usr/bin/env bash
# Usage: ./mem_profile.sh
# Runs memory_profiler (mprof) on the game and produces a plot + raw CSV.

# Ensure mprof is installed (pip install memory_profiler)

# Run the game under mprof to capture memory over time
mprof run --python src/main.py
# Produce a PNG plot for quick visual inspection
mprof plot --output scripts/profiling/memory_plot.png
# Dump raw data to CSV (default is .dat, we convert to csv for easier diff)
mprof dump -f scripts/profiling/memory_raw.csv
