"""Metrics JSON helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from switch_model.config import SwitchConfig
from switch_model.model import NoiseSimulationResult, ParasiticSimulationResult, RonSimulationResult


def build_switch_metrics(
    cfg: SwitchConfig,
    *,
    ron: RonSimulationResult | None = None,
    noise: NoiseSimulationResult | None = None,
    parasitics: ParasiticSimulationResult | None = None,
) -> dict[str, Any]:
    """Build metrics dictionary for JSON export."""
    report: dict[str, Any] = {
        "switch_type": cfg.switch_type.value,
        "fch_hz": cfg.fch_hz,
        "parasitics": cfg.effective_parasitic_caps(),
    }
    if ron is not None:
        report["ron"] = {
            "ron_min_ohm": ron["metrics"].ron_min_ohm,
            "ron_max_ohm": ron["metrics"].ron_max_ohm,
            "ron_at_vcm_ohm": ron["metrics"].ron_at_vcm_ohm,
            "linearity_error_pct": ron["metrics"].linearity_error_pct,
        }
    if noise is not None:
        report["noise"] = {
            "flicker_corner_hz": noise["flicker_corner_hz"],
            "noise_at_1hz_v_per_sqrt_hz": float(noise["noise_v_per_sqrt_hz"][0]),
        }
    if parasitics is not None:
        report["charge_injection"] = {
            "q_inj_coulomb": parasitics["charge"].q_inj_coulomb,
            "v_inj_v": parasitics["charge"].v_inj_v,
            "dummy_reduction_pct": parasitics["charge"].dummy_reduction_pct,
        }
        report["clock_feedthrough"] = {
            "v_feedthrough_v": parasitics["feedthrough"].v_feedthrough_v,
            "attenuation_db": parasitics["feedthrough"].attenuation_db,
        }
    return report


def write_metrics_json(path: Path, metrics: dict[str, Any]) -> None:
    """Write metrics JSON, merging with existing content if present."""
    path.parent.mkdir(parents=True, exist_ok=True)
    merged: dict[str, Any] = {}
    if path.is_file():
        merged = json.loads(path.read_text(encoding="utf-8"))
    merged.update(metrics)
    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
