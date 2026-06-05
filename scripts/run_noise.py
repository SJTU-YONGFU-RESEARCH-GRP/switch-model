#!/usr/bin/env python3
"""Channel noise spectrum for MOS switch macromodels."""

from __future__ import annotations

import argparse
from pathlib import Path

from switch_model.cli_helpers import (
    add_noise_args,
    add_output_args,
    add_simulator_args,
    add_switch_args,
    build_switch_config,
    resolve_engine_label,
)
from switch_model.io import write_noise_csv
from switch_model.metrics import build_switch_metrics, write_metrics_json
from switch_model.model import simulate_noise
from switch_model.ngspice_engine import NgspiceNotFoundError, simulate_noise_ngspice
from switch_model.plotting import plot_noise_spectrum
from switch_model.report import write_noise_report
from switch_model.spectre_engine import SpectreNotFoundError, simulate_noise_spectre


def main() -> None:
    """Run noise simulation and write CSV, SVG, metrics, and report."""
    parser = argparse.ArgumentParser(description="MOS switch noise testbench.")
    add_switch_args(parser)
    add_noise_args(parser)
    add_simulator_args(parser)
    add_output_args(parser)
    args = parser.parse_args()

    cfg = build_switch_config(args)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.simulator == "python":
            result = simulate_noise(cfg)
        elif args.simulator == "ngspice":
            result = simulate_noise_ngspice(cfg, out_dir)
        elif args.simulator == "spectre":
            result = simulate_noise_spectre(cfg, out_dir)
        else:
            raise ValueError(f"Unknown simulator: {args.simulator}")
    except (NgspiceNotFoundError, SpectreNotFoundError) as exc:
        raise SystemExit(str(exc)) from exc

    engine = resolve_engine_label(args.simulator)
    write_noise_csv(
        out_dir / "noise_spectrum.csv",
        result["frequency_hz"],
        result["noise_v_per_sqrt_hz"],
    )
    plot_noise_spectrum(
        result["frequency_hz"],
        result["noise_v_per_sqrt_hz"],
        out_dir / "noise_spectrum.svg",
        title=f"Channel noise ({engine})",
        flicker_corner_hz=result["flicker_corner_hz"],
    )
    write_metrics_json(out_dir / "switch_metrics.json", build_switch_metrics(cfg, noise=result))
    write_noise_report(
        out_dir / "NOISE_REPORT.md",
        switch_type=cfg.switch_type.value,
        flicker_corner_hz=result["flicker_corner_hz"],
    )
    print(f"Wrote noise results to {out_dir}")


if __name__ == "__main__":
    main()
