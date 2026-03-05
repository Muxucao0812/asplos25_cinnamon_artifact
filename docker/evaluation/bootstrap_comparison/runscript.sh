#!/bin/bash
# Run bootstrap comparison simulations and generate bootstrap_comparison.pdf
set -eou pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR=/cinnamon_artifact/outputs
RESULTS_DIR=${OUTPUT_DIR}/bootstrap_results
SST_BIN=/cinnamon_artifact/simulator/build/install/sst-core/bin/sst
TRACE_DIR=${SCRIPT_DIR}/traces

mkdir -p "${RESULTS_DIR}"

# ---------------------------------------------------------------------------
# Helper: run one simulation configuration and save its log
# ---------------------------------------------------------------------------
run_sim() {
    local label="$1"
    local num_chiplets="$2"
    local extra_args="${3:-}"
    local log="${RESULTS_DIR}/${label}.log"

    echo "Running: ${label} ..."
    # shellcheck disable=SC2086
    ${SST_BIN} "${SCRIPT_DIR}/cinnamon_config.py" -- \
        --num_chiplets "${num_chiplets}" \
        --trace_dir "${TRACE_DIR}/bootstrap_${num_chiplets}chiplet" \
        ${extra_args} \
        2>&1 | tee "${log}"
    echo "Done:    ${label}"
}

# ---------------------------------------------------------------------------
# Simulation configurations
# ---------------------------------------------------------------------------
run_sim "cinnamon_1chiplet" 1
run_sim "cinnamon_2chiplet" 2
run_sim "cinnamon_4chiplet" 4
run_sim "cinnamon_8chiplet" 8

# ---------------------------------------------------------------------------
# Generate figure
# ---------------------------------------------------------------------------
echo "Plotting bootstrap comparison ..."
python3 "${SCRIPT_DIR}/plot.py" \
    --results_dir "${RESULTS_DIR}" \
    --output      "${OUTPUT_DIR}/bootstrap_comparison.pdf"

echo "bootstrap_comparison.pdf written to ${OUTPUT_DIR}"
