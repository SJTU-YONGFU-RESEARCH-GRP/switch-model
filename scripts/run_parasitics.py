#!/usr/bin/env python3
"""Charge injection and clock feedthrough metrics."""

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
from switch_model.metrics import build_switch_metrics, write_metrics_json
from switch_model.model import simulate_parasitics
from switch_model.ngspice_engine import NgspiceNotFoundError, simulate_parasitics_ngspice
from switch_model.spectre_engine import SpectreNotFoundError, simulate_parasitics_spectre
from switch_model.plotting import plot_parasitics_summary
from switch_model.report import refresh_reports_after_bench, write_parasitics_report


def main() -> None:
    """Compute parasitic metrics and write JSON."""
    parser = argparse.ArgumentParser(description="MOS switch parasitics testbench.")
    add_switch_args(parser)
    add_noise_args(parser)
    add_simulator_args(parser)
    add_output_args(parser)
    args = parser.parse_args()

    cfg = build_switch_config(args)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    parasitics_source = args.simulator
    try:
        if args.simulator == "python":
            result = simulate_parasitics(cfg)
            parasitics_source = "python"
        elif args.simulator == "ngspice":
            result = simulate_parasitics_ngspice(cfg, out_dir)
            if (out_dir / "logs" / "ngspice_parasitics_fallback.log").is_file():
                parasitics_source = "python_fallback"
            else:
                parasitics_source = "ngspice_behavioral"
        elif args.simulator == "spectre":
            result = simulate_parasitics_spectre(cfg, out_dir)
            if (out_dir / "logs" / "spectre_parasitics_fallback.log").is_file():
                parasitics_source = "python_fallback"
            else:
                parasitics_source = "spectre_behavioral"
        else:
            raise ValueError(f"Unknown simulator: {args.simulator}")
    except (NgspiceNotFoundError, SpectreNotFoundError) as exc:
        raise SystemExit(str(exc)) from exc

    engine = resolve_engine_label(args.simulator)
    metrics = build_switch_metrics(
        cfg,
        parasitics=result,
        engine=args.simulator,
        parasitics_source=parasitics_source,
    )
    write_metrics_json(out_dir / "switch_metrics.json", metrics)

    charge = result["charge"]
    feed = result["feedthrough"]
    plot_parasitics_summary(
        charge,
        feed,
        out_dir / "parasitics_summary.svg",
        title=f"Parasitics ({engine})",
        switch_type=cfg.switch_type.value,
    )
    write_parasitics_report(
        out_dir / "PARASITICS_REPORT.md",
        switch_type=cfg.switch_type.value,
        q_inj_coulomb=charge.q_inj_coulomb,
        v_inj_v=charge.v_inj_v,
        dummy_reduction_pct=charge.dummy_reduction_pct,
        v_feedthrough_v=feed.v_feedthrough_v,
        attenuation_db=feed.attenuation_db,
    )
    for report_path in refresh_reports_after_bench(out_dir, switch_type=cfg.switch_type.value):
        print(f"Updated {report_path}")
    print(f"Switch type: {cfg.switch_type.value}")
    print(f"Engine: {engine} (parasitics_source={parasitics_source})")
    print(f"Charge injection: Q={charge.q_inj_coulomb:.3e} C, V_inj={charge.v_inj_v:.3e} V")
    print(f"Dummy reduction: {charge.dummy_reduction_pct:.1f} %")
    print(
        f"Clock feedthrough: V_cf={feed.v_feedthrough_v:.3e} V, "
        f"atten={feed.attenuation_db:.1f} dB"
    )
    print(f"Wrote metrics to {out_dir / 'switch_metrics.json'}")


if __name__ == "__main__":
    main()
