#!/usr/bin/env python3
"""Charge injection and clock feedthrough metrics."""

from __future__ import annotations

import argparse
from pathlib import Path

from switch_model.cli_helpers import (
    add_noise_args,
    add_output_args,
    add_switch_args,
    build_switch_config,
)
from switch_model.metrics import build_switch_metrics, write_metrics_json
from switch_model.model import simulate_parasitics
from switch_model.report import write_parasitics_report


def main() -> None:
    """Compute parasitic metrics and write JSON."""
    parser = argparse.ArgumentParser(description="MOS switch parasitics testbench.")
    add_switch_args(parser)
    add_noise_args(parser)
    add_output_args(parser)
    args = parser.parse_args()

    cfg = build_switch_config(args)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = simulate_parasitics(cfg)
    metrics = build_switch_metrics(cfg, parasitics=result)
    write_metrics_json(out_dir / "switch_metrics.json", metrics)

    charge = result["charge"]
    feed = result["feedthrough"]
    write_parasitics_report(
        out_dir / "PARASITICS_REPORT.md",
        switch_type=cfg.switch_type.value,
        q_inj_coulomb=charge.q_inj_coulomb,
        v_inj_v=charge.v_inj_v,
        dummy_reduction_pct=charge.dummy_reduction_pct,
        v_feedthrough_v=feed.v_feedthrough_v,
        attenuation_db=feed.attenuation_db,
    )
    print(f"Switch type: {cfg.switch_type.value}")
    print(f"Charge injection: Q={charge.q_inj_coulomb:.3e} C, V_inj={charge.v_inj_v:.3e} V")
    print(f"Dummy reduction: {charge.dummy_reduction_pct:.1f} %")
    print(
        f"Clock feedthrough: V_cf={feed.v_feedthrough_v:.3e} V, "
        f"atten={feed.attenuation_db:.1f} dB"
    )
    print(f"Wrote metrics to {out_dir / 'switch_metrics.json'}")


if __name__ == "__main__":
    main()
