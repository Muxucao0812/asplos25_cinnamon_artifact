#!/bin/bash
# Run performance benchmarks and generate performance PDFs + table.
# Note: this script can take approximately one day to complete.
set -eou pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR=/cinnamon_artifact/outputs
RESULTS_DIR=${OUTPUT_DIR}/performance_results
SST_BIN=/cinnamon_artifact/simulator/build/install/sst-core/bin/sst
TRACE_DIR=${SCRIPT_DIR}/traces

mkdir -p "${RESULTS_DIR}"

# ---------------------------------------------------------------------------
# Helper: run one simulation configuration and save its log
# ---------------------------------------------------------------------------
run_sim() {
    local label="$1"
    local num_chiplets="$2"
    local workload="$3"
    local extra_args="${4:-}"
    local log="${RESULTS_DIR}/${workload}_${num_chiplets}chiplet.log"

    echo "Running: ${workload} with ${num_chiplets} chiplet(s) ..."
    # shellcheck disable=SC2086
    ${SST_BIN} "${SCRIPT_DIR}/cinnamon_config.py" -- \
        --num_chiplets "${num_chiplets}" \
        --trace_dir "${TRACE_DIR}/${workload}_${num_chiplets}chiplet" \
        ${extra_args} \
        2>&1 | tee "${log}"
    echo "Done:    ${workload} ${num_chiplets}-chiplet"
}

# ---------------------------------------------------------------------------
# Workloads and chiplet configurations
# ---------------------------------------------------------------------------
WORKLOADS=("resnet20" "squeezenet" "mnist_fc" "bert_tiny")
CHIPLETS=(1 2 4 8)

for workload in "${WORKLOADS[@]}"; do
    for nc in "${CHIPLETS[@]}"; do
        run_sim "${workload}_${nc}chiplet" "${nc}" "${workload}"
    done
done

# ---------------------------------------------------------------------------
# Generate figures and table
# ---------------------------------------------------------------------------
echo "Plotting performance ..."
python3 "${SCRIPT_DIR}/plot.py" \
    --results_dir "${RESULTS_DIR}" \
    --output_dir  "${OUTPUT_DIR}"

echo "performance.pdf, performance_per_dollar.pdf, and performance_table.txt"
echo "written to ${OUTPUT_DIR}"
