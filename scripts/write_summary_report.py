#!/usr/bin/env python3
"""Regenerate top-level REPORT.md and per-switch REPORT.md files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from switch_model.report import SWITCH_TYPES, write_summary_report, write_switch_type_report


def main() -> None:
    """Write summary and per-switch Markdown reports from existing artifacts."""
    parser = argparse.ArgumentParser(description="Build switch-model summary REPORT.md.")
    parser.add_argument(
        "--output-root",
        type=str,
        default="outputs/python",
        help="Root output directory containing per-switch subfolders.",
    )
    args = parser.parse_args()

    output_root = Path(args.output_root)
    for stype in SWITCH_TYPES:
        sub = output_root / stype
        if sub.is_dir():
            write_switch_type_report(sub, switch_type=stype)

    path = write_summary_report(output_root)
    if path is None:
        print(f"No comparison JSON found under {output_root}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
