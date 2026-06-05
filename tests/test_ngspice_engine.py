"""Tests for ngspice engine integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from switch_model.config import SwitchConfig, SwitchType
from switch_model.io import package_root
from switch_model.netlist import ngspice_ron_probe_expr
from switch_model.ngspice_engine import (
    NgspiceNotFoundError,
    find_ngspice_executable,
    render_ngspice_ron_netlist,
    simulate_ron_ngspice,
)


def test_pmos_ron_probe_expr_matches_python_thresholds() -> None:
    """PMOS B-source should gate on vgs < vth_p and vgs_eff > 1e-6 (no max floor)."""
    cfg = SwitchConfig(switch_type=SwitchType.PMOS)
    expr = ngspice_ron_probe_expr(cfg)
    assert "max(" not in expr
    assert ">1e-6)" in expr
    assert f"<{cfg.vth_p_v})" in expr
    assert "1-(" in expr


def test_render_ngspice_netlist_contains_probe() -> None:
    """Rendered netlist should include Ron probe expression."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    template = package_root() / "testbench" / "ngspice" / "ron_sweep.cir"
    text = render_ngspice_ron_netlist(template, cfg)
    assert "Bprobe" in text
    assert "V(clk)" in text


@pytest.mark.parametrize("switch_type", [SwitchType.NMOS, SwitchType.PMOS, SwitchType.CMOS])
def test_simulate_ron_ngspice_matches_python(
    tmp_path: Path, switch_type: SwitchType
) -> None:
    """ngspice Ron sweep should track Python macromodel within tolerance."""
    try:
        find_ngspice_executable()
    except NgspiceNotFoundError:
        pytest.skip("ngspice not available")

    import numpy as np

    from switch_model.model import simulate_ron_sweep

    cfg = SwitchConfig(switch_type=switch_type)
    py = simulate_ron_sweep(cfg)
    ng = simulate_ron_ngspice(cfg, tmp_path / switch_type.value)
    ron_interp = np.interp(py["vin_v"], ng["vin_v"], ng["ron_ohm"])
    mask = py["ron_ohm"] < cfg.roff_ohm * 0.5
    rel = abs(py["ron_ohm"][mask] - ron_interp[mask]) / py["ron_ohm"][mask]
    assert float(rel.max()) < 0.02


def test_simulate_ron_ngspice_pmos_matches_python(tmp_path: Path) -> None:
    """PMOS ngspice Ron should track Python within 0.1% (boundary + ron_max)."""
    try:
        find_ngspice_executable()
    except NgspiceNotFoundError:
        pytest.skip("ngspice not available")

    import numpy as np

    from switch_model.model import simulate_ron_sweep

    cfg = SwitchConfig(switch_type=SwitchType.PMOS)
    py = simulate_ron_sweep(cfg)
    ng = simulate_ron_ngspice(cfg, tmp_path)
    mask = py["ron_ohm"] < cfg.roff_ohm * 0.5
    rel = abs(py["ron_ohm"][mask] - ng["ron_ohm"][mask]) / py["ron_ohm"][mask]
    assert float(rel.max()) < 0.001
    assert abs(py["metrics"].ron_max_ohm - ng["metrics"].ron_max_ohm) / py["metrics"].ron_max_ohm < 0.001
    assert float(ng["vin_v"][-1]) == pytest.approx(float(py["vin_v"][-1]), abs=1.0e-9)
    assert float(ng["ron_ohm"][-1]) == pytest.approx(float(py["ron_ohm"][-1]), rel=0.01)
