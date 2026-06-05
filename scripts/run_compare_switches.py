#!/usr/bin/env python3
"""Compare all switch types (Ron linearity, noise, parasitics)."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from switch_model.config import SwitchConfig, SwitchType
from switch_model.metrics import build_switch_metrics
from switch_model.model import simulate_noise, simulate_parasitics, simulate_ron_sweep


def main() -> None:
    """Run comparison across all switch topologies."""
    parser = argparse.ArgumentParser(description="Compare MOS switch types.")
    parser.add_argument("--output-dir", type=str, default="outputs/compare")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = SwitchConfig()
    comparison: dict[str, dict] = {}
    for stype in SwitchType:
        cfg = replace(base, switch_type=stype)
        ron = simulate_ron_sweep(cfg)
        noise = simulate_noise(cfg)
        parasitics = simulate_parasitics(cfg)
        comparison[stype.value] = build_switch_metrics(
            cfg, ron=ron, noise=noise, parasitics=parasitics
        )

    out_path = out_dir / "switch_comparison.json"
    out_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(f"Wrote comparison to {out_path}")


if __name__ == "__main__":
    main()
