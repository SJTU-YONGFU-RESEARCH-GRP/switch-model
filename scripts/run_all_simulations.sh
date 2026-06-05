#!/usr/bin/env bash
# Run all switch-model Python benches.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_ROOT="${1:-${ROOT_DIR}/outputs/python}"

cd "${ROOT_DIR}"

if [[ -f "${ROOT_DIR}/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/.venv/bin/activate"
fi

for stype in nmos pmos cmos nmos_dummy bs bs_dummy; do
    out="${OUTPUT_ROOT}/${stype}"
    python scripts/run_ron.py --switch-type "${stype}" --output-dir "${out}"
    python scripts/run_noise.py --switch-type "${stype}" --output-dir "${out}"
    python scripts/run_parasitics.py --switch-type "${stype}" --output-dir "${out}"
done

python scripts/run_compare_switches.py --output-dir "${OUTPUT_ROOT}/compare"
python scripts/write_summary_report.py --output-root "${OUTPUT_ROOT}"
echo "All benches complete under ${OUTPUT_ROOT}"
echo "Open ${OUTPUT_ROOT}/REPORT.md for the summary with figures."
