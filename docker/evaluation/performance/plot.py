#!/usr/bin/env python3
"""
Plot performance figures and generate performance_table.txt.

Reads per-workload timing files produced by runscript.sh and generates:
  performance.pdf          - throughput bar chart (inferences/second)
  performance_per_dollar.pdf - throughput-per-dollar bar chart
  performance_table.txt    - summary table

Each timing file has one line per chiplet in the form:
  Completed at: <nanoseconds> ns
The end-to-end latency is taken as the maximum across all chiplets.
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
parser.add_argument("--results_dir",  type=str, required=True,
                    help="Directory containing per-workload .log files")
parser.add_argument("--output_dir",   type=str, required=True,
                    help="Directory where output files are written")
# Cost model: approximate chip price in USD for scaling
parser.add_argument("--chip_cost_usd", type=float, default=10000.0,
                    help="Estimated chip cost in USD for performance-per-dollar")
args = parser.parse_args()

os.makedirs(args.output_dir, exist_ok=True)

# ---------------------------------------------------------------------------
# Workloads and their display labels
# The runscript writes <workload>_<num_chiplets>chiplet.log for each run.
# ---------------------------------------------------------------------------
WORKLOADS = [
    ("ResNet-20",   "resnet20"),
    ("SqueezeNet",  "squeezenet"),
    ("MNIST-FC",    "mnist_fc"),
    ("BERT-Tiny",   "bert_tiny"),
]

CHIPLET_CONFIGS = [1, 2, 4, 8]

COLORS = ["#4878CF", "#6ACC65", "#D65F5F", "#B47CC7",
          "#FAA43A", "#60BD68", "#F17CB0", "#B2912F"]

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
# Collect results: results[workload_label][num_chiplets] = latency_s
# ---------------------------------------------------------------------------
results = {}

for wl_label, wl_key in WORKLOADS:
    results[wl_label] = {}
    for nc in CHIPLET_CONFIGS:
        fname = "{}_{}chiplet.log".format(wl_key, nc)
        log_path = os.path.join(args.results_dir, fname)
        if not os.path.isfile(log_path):
            print("WARNING: missing log {}; skipping".format(log_path))
            continue
        ns = parse_latency_ns(log_path)
        results[wl_label][nc] = ns / 1e9   # ns -> s

if not any(results[k] for k in results):
    print("ERROR: no results found in {}".format(args.results_dir))
    sys.exit(1)

# ---------------------------------------------------------------------------
# Derived metrics
# throughput (inferences/s) = 1 / latency_s
# throughput_per_dollar = throughput / (num_chiplets * chip_cost)
# ---------------------------------------------------------------------------
def throughput(lat_s):
    return 1.0 / lat_s if lat_s > 0 else 0.0

def tpd(lat_s, num_chiplets):
    tp = throughput(lat_s)
    cost = num_chiplets * args.chip_cost_usd
    return tp / cost if cost > 0 else 0.0

# ---------------------------------------------------------------------------
# Helper: grouped bar chart
# ---------------------------------------------------------------------------
def grouped_bar(ax, workloads, configs, values, ylabel, title):
    """
    workloads: list of workload labels (x-axis groups)
    configs:   list of configuration labels (one bar per group)
    values:    2-D list [workload_idx][config_idx]
    """
    n_wl   = len(workloads)
    n_cfg  = len(configs)
    x      = np.arange(n_wl)
    width  = 0.8 / n_cfg

    for ci, cfg_label in enumerate(configs):
        offsets = x - 0.4 + width * ci + width / 2
        vals    = [values[wi][ci] for wi in range(n_wl)]
        ax.bar(offsets, vals, width, label=cfg_label,
               color=COLORS[ci % len(COLORS)],
               edgecolor="black", linewidth=0.6)

    ax.set_xlabel("Workload", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(workloads, rotation=15, ha="right", fontsize=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9)

# ---------------------------------------------------------------------------
# Build value matrices
# ---------------------------------------------------------------------------
present_configs = sorted({nc for wl in results.values() for nc in wl})
config_labels   = ["{}-chiplet".format(nc) for nc in present_configs]
wl_labels       = [wl for wl, _ in WORKLOADS if results[wl]]

tp_matrix  = []   # [workload][config]
tpd_matrix = []

for wl_label in wl_labels:
    tp_row  = []
    tpd_row = []
    for nc in present_configs:
        lat = results[wl_label].get(nc, 0)
        tp_row.append(throughput(lat))
        tpd_row.append(tpd(lat, nc))
    tp_matrix.append(tp_row)
    tpd_matrix.append(tpd_row)

# ---------------------------------------------------------------------------
# Figure 1: Throughput (inferences/second)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))
grouped_bar(ax, wl_labels, config_labels, tp_matrix,
            "Throughput (inferences/s)",
            "Cinnamon Performance")
plt.tight_layout()
perf_pdf = os.path.join(args.output_dir, "performance.pdf")
plt.savefig(perf_pdf, format="pdf", bbox_inches="tight")
print("Saved {}".format(perf_pdf))

# ---------------------------------------------------------------------------
# Figure 2: Throughput per dollar
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))
grouped_bar(ax, wl_labels, config_labels, tpd_matrix,
            "Throughput per dollar (inferences/s/$)",
            "Cinnamon Performance per Dollar")
plt.tight_layout()
tpd_pdf = os.path.join(args.output_dir, "performance_per_dollar.pdf")
plt.savefig(tpd_pdf, format="pdf", bbox_inches="tight")
print("Saved {}".format(tpd_pdf))

# ---------------------------------------------------------------------------
# Table: performance_table.txt
# ---------------------------------------------------------------------------
table_path = os.path.join(args.output_dir, "performance_table.txt")
col_w = 20
with open(table_path, "w") as f:
    # Header
    header = "Workload".ljust(col_w)
    for nc in present_configs:
        header += "{}-chiplet Lat(ms)".format(nc).ljust(col_w)
        header += "{}-chiplet Tput(inf/s)".format(nc).ljust(col_w)
    f.write(header + "\n")
    f.write("-" * len(header) + "\n")

    for wi, wl_label in enumerate(wl_labels):
        row = wl_label.ljust(col_w)
        for ci, nc in enumerate(present_configs):
            lat = results[wl_label].get(nc, None)
            if lat is None:
                row += "N/A".ljust(col_w) + "N/A".ljust(col_w)
            else:
                row += "{:.2f}".format(lat * 1e3).ljust(col_w)
                row += "{:.4f}".format(throughput(lat)).ljust(col_w)
        f.write(row + "\n")

print("Saved {}".format(table_path))
