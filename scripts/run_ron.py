#!/usr/bin/env python3
"""Ron versus Vin sweep for MOS switch macromodels."""

from __future__ import annotations

import argparse
from pathlib import Path

from switch_model.cli_helpers import (
    add_noise_args,
    add_output_args,
    add_switch_args,
    build_switch_config,
)
from switch_model.io import write_ron_csv
from switch_model.metrics import build_switch_metrics, write_metrics_json
from switch_model.model import simulate_ron_sweep
from switch_model.plotting import plot_ron_sweep
from switch_model.report import write_ron_report


def main() -> None:
    """Run Ron sweep and write CSV, SVG, metrics, and report."""
    parser = argparse.ArgumentParser(description="MOS switch Ron testbench.")
    add_switch_args(parser)
    add_noise_args(parser)
    add_output_args(parser)
    args = parser.parse_args()

    cfg = build_switch_config(args)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = simulate_ron_sweep(cfg)
    write_ron_csv(out_dir / "ron_sweep.csv", result["vin_v"], result["ron_ohm"])
    plot_ron_sweep(
        result["vin_v"],
        result["ron_ohm"],
        out_dir / "ron_sweep.svg",
        title="Signal-dependent Ron",
        switch_type=cfg.switch_type.value,
    )
    write_metrics_json(out_dir / "switch_metrics.json", build_switch_metrics(cfg, ron=result))
    write_ron_report(
        out_dir / "RON_REPORT.md",
        switch_type=cfg.switch_type.value,
        ron_min_ohm=result["metrics"].ron_min_ohm,
        ron_max_ohm=result["metrics"].ron_max_ohm,
        linearity_error_pct=result["metrics"].linearity_error_pct,
    )
    print(f"Wrote Ron results to {out_dir}")


if __name__ == "__main__":
    main()
