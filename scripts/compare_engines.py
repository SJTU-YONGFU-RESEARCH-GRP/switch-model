#!/usr/bin/env python3
"""Compare switch_metrics.json across python, ngspice, and spectre engines."""

from __future__ import annotations

import argparse
from pathlib import Path

from switch_model.compare import DEFAULT_ENGINES, compare_engines, format_compare_table
from switch_model.io import package_root
from switch_model.report import write_engine_comparison_report


def main() -> None:
    """Load per-engine metrics, print spread table, write outputs/REPORT.md."""
    parser = argparse.ArgumentParser(
        description="Compare switch metrics across simulation engines.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs"),
        help="Root directory containing <engine>/<type>/switch_metrics.json.",
    )
    parser.add_argument(
        "--engines",
        nargs="+",
        default=list(DEFAULT_ENGINES),
        help=f"Engines to compare (default: {' '.join(DEFAULT_ENGINES)}).",
    )
    args = parser.parse_args()

    root = args.output_root
    if not root.is_absolute():
        root = package_root() / root

    result = compare_engines(root, engines=tuple(args.engines))
    print(format_compare_table(result))
    report_path = write_engine_comparison_report(root, result, engines=tuple(args.engines))
    print(f"Wrote {report_path}")
    if not result.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
