#!/usr/bin/env python3
"""
Plot bootstrap comparison figure.

Reads per-configuration timing files produced by runscript.sh and generates
bootstrap_comparison.pdf in the outputs directory.

Each timing file has one line per chiplet in the form:
  Completed at: <nanoseconds> ns
The latency of the bootstrap is taken as the maximum across all chiplets.
"""

import sys
import os
import re
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--results_dir", type=str, required=True,
                    help="Directory containing per-configuration .log files")
parser.add_argument("--output",      type=str, required=True,
                    help="Output PDF file path")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Configuration labels and file names produced by runscript.sh
# ---------------------------------------------------------------------------
CONFIGS = [
    ("Cinnamon 1-chiplet",  "cinnamon_1chiplet"),
    ("Cinnamon 2-chiplet",  "cinnamon_2chiplet"),
    ("Cinnamon 4-chiplet",  "cinnamon_4chiplet"),
    ("Cinnamon 8-chiplet",  "cinnamon_8chiplet"),
]

# ---------------------------------------------------------------------------
# Parse timing from a log file
# ---------------------------------------------------------------------------
def parse_latency_ns(log_path):
    """Return the maximum 'Completed at' time (ns) found in log_path."""
    pattern = re.compile(r"Completed at:\s+([\d]+)\s+ns")
    max_ns = 0
    with open(log_path) as f:
        for line in f:
            m = pattern.search(line)
            if m:
                max_ns = max(max_ns, int(m.group(1)))
    if max_ns == 0:
        raise ValueError("No timing found in {}".format(log_path))
    return max_ns

# ---------------------------------------------------------------------------
# Collect results
# ---------------------------------------------------------------------------
labels    = []
latencies = []   # in milliseconds

for label, fname in CONFIGS:
    log_path = os.path.join(args.results_dir, fname + ".log")
    if not os.path.isfile(log_path):
        print("WARNING: missing log file {}; skipping".format(log_path))
        continue
    ns = parse_latency_ns(log_path)
    labels.append(label)
    latencies.append(ns / 1e6)   # ns -> ms

if not labels:
    print("ERROR: no results found in {}".format(args.results_dir))
    sys.exit(1)

# ---------------------------------------------------------------------------
# Draw bar chart
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 5))

x      = np.arange(len(labels))
width  = 0.5
colors = ["#4878CF", "#6ACC65", "#D65F5F", "#B47CC7"]

bars = ax.bar(x, latencies, width,
              color=colors[:len(labels)],
              edgecolor="black", linewidth=0.8)

ax.set_xlabel("Configuration", fontsize=12)
ax.set_ylabel("Bootstrap latency (ms)", fontsize=12)
ax.set_title("Bootstrap Latency Comparison", fontsize=14)
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=10)
ax.yaxis.grid(True, linestyle="--", alpha=0.7)
ax.set_axisbelow(True)

for bar, val in zip(bars, latencies):
    ax.text(bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + max(latencies) * 0.01,
            "{:.2f}".format(val),
            ha="center", va="bottom", fontsize=9)

plt.tight_layout()
os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
plt.savefig(args.output, format="pdf", bbox_inches="tight")
print("Saved {}".format(args.output))
