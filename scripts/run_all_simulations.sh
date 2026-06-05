#!/usr/bin/env bash
# Run all switch-model benches for python, ngspice, and spectre engines.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_ROOT="${OUTPUT_ROOT:-${ROOT_DIR}/outputs}"
SKIP_MISSING=0

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Run Ron, noise, and parasitics for all switch types under:
  \${OUTPUT_ROOT}/{python,ngspice,spectre}/

Options:
  --output-root DIR   Base output directory (default: ${ROOT_DIR}/outputs).
  --skip-missing      Skip ngspice/spectre when binaries are absent or fail.
  -h, --help          Show this message.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
        --skip-missing) SKIP_MISSING=1; shift ;;
        -h | --help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

cd "${ROOT_DIR}"

if [[ -f "${ROOT_DIR}/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/.venv/bin/activate"
fi

PYTHON="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
    PYTHON="python3"
fi

run_engine() {
    local engine="$1"
    local out="${OUTPUT_ROOT}/${engine}"

    if [[ "${engine}" != "python" ]]; then
        if [[ "${SKIP_MISSING}" -eq 1 ]]; then
            if [[ "${engine}" == "ngspice" ]] && ! command -v ngspice >/dev/null 2>&1; then
                echo "Skipping ngspice — not on PATH."
                return 0
            fi
            if [[ "${engine}" == "spectre" ]] && ! command -v spectre >/dev/null 2>&1 \
                && [[ ! -x /eda/cadence/SPECTRE241/tools/bin/spectre ]]; then
                echo "Skipping spectre — not on PATH."
                return 0
            fi
        fi
    fi

    echo "=== Engine: ${engine} ==="
    for stype in nmos pmos cmos nmos_dummy bs bs_dummy; do
        sub="${out}/${stype}"
        if ! "${PYTHON}" scripts/run_ron.py --simulator "${engine}" --switch-type "${stype}" --output-dir "${sub}"; then
            if [[ "${SKIP_MISSING}" -eq 1 ]]; then
                echo "Warning: run_ron failed for ${engine}/${stype}" >&2
            else
                return 1
            fi
        fi
        if ! "${PYTHON}" scripts/run_noise.py --simulator "${engine}" --switch-type "${stype}" --output-dir "${sub}"; then
            if [[ "${SKIP_MISSING}" -eq 1 ]]; then
                echo "Warning: run_noise failed for ${engine}/${stype}" >&2
            else
                return 1
            fi
        fi
        "${PYTHON}" scripts/run_parasitics.py --switch-type "${stype}" --output-dir "${sub}" || true
    done

    "${PYTHON}" scripts/run_compare_switches.py --output-dir "${out}/compare" || true
    "${PYTHON}" scripts/write_summary_report.py --output-root "${out}" || true
}

for engine in python ngspice spectre; do
    run_engine "${engine}"
done

echo "=== Engine comparison ==="
"${PYTHON}" scripts/compare_engines.py --output-root "${OUTPUT_ROOT}" || true

echo "Batch complete under ${OUTPUT_ROOT}/"
echo "Open ${OUTPUT_ROOT}/REPORT.md for cross-engine summary."
