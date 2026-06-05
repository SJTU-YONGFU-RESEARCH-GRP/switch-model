"""Tests for ngspice engine integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from switch_model.config import SwitchConfig, SwitchType
from switch_model.io import package_root
from switch_model.ngspice_engine import (
    NgspiceNotFoundError,
    find_ngspice_executable,
    render_ngspice_ron_netlist,
    simulate_ron_ngspice,
)


def test_render_ngspice_netlist_contains_probe() -> None:
    """Rendered netlist should include Ron probe expression."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    template = package_root() / "testbench" / "ngspice" / "ron_sweep.cir"
    text = render_ngspice_ron_netlist(template, cfg)
    assert "Bprobe" in text
    assert "V(clk)" in text


def test_simulate_ron_ngspice_matches_python(tmp_path: Path) -> None:
    """ngspice Ron sweep should track Python macromodel within tolerance."""
    try:
        find_ngspice_executable()
    except NgspiceNotFoundError:
        pytest.skip("ngspice not available")

    from switch_model.model import simulate_ron_sweep

    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    import numpy as np

    py = simulate_ron_sweep(cfg)
    ng = simulate_ron_ngspice(cfg, tmp_path)
    ron_interp = np.interp(py["vin_v"], ng["vin_v"], ng["ron_ohm"])
    mask = py["ron_ohm"] < cfg.roff_ohm * 0.5
    rel = abs(py["ron_ohm"][mask] - ron_interp[mask]) / py["ron_ohm"][mask]
    assert float(rel.max()) < 0.02
