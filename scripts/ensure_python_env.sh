#!/usr/bin/env bash
# Ensure switch-model is importable: create venv + editable install if needed.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    echo "Python environment not found; running scripts/install_python.sh ..."
    "${ROOT_DIR}/scripts/install_python.sh" --no-dev
fi

# shellcheck disable=SC1091
source "${ROOT_DIR}/.venv/bin/activate"
export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
