"""ngspice parasitics bench tests (skip when ngspice is not installed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from switch_model.config import SwitchConfig, SwitchType
from switch_model.io import package_root
from switch_model.model import simulate_parasitics
from switch_model.ngspice_engine import (
    NgspiceNotFoundError,
    render_ngspice_parasitics_netlist,
    simulate_parasitics_ngspice,
)

pytestmark = pytest.mark.skipif(
    __import__("shutil").which("ngspice") is None
    and __import__("shutil").which("ngspice-shared") is None,
    reason="ngspice not on PATH",
)


def test_render_parasitics_netlist_has_control_metrics() -> None:
    """Rendered parasitics netlist embeds charge and feedthrough literals."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS_DUMMY)
    template = package_root() / "testbench" / "ngspice" / "parasitics_bench.cir"
    text = render_ngspice_parasitics_netlist(template, cfg)
    assert "wrdata parasitics.raw" in text
    assert "PLACEHOLDER_" not in text
    assert "dummy_reduction_pct" in text


def test_ngspice_parasitics_matches_python(tmp_path: Path) -> None:
    """ngspice parasitics metrics should match Python macromodel."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    py = simulate_parasitics(cfg)
    try:
        ng = simulate_parasitics_ngspice(cfg, tmp_path)
    except NgspiceNotFoundError:
        pytest.skip("ngspice not available")
    assert not (tmp_path / "logs" / "ngspice_parasitics_fallback.log").is_file()
    assert py["charge"].q_inj_coulomb == pytest.approx(ng["charge"].q_inj_coulomb, rel=1e-6)
    assert py["charge"].v_inj_v == pytest.approx(ng["charge"].v_inj_v, rel=1e-6)
    assert py["feedthrough"].v_feedthrough_v == pytest.approx(
        ng["feedthrough"].v_feedthrough_v, rel=1e-6
    )
    assert py["feedthrough"].attenuation_db == pytest.approx(
        ng["feedthrough"].attenuation_db, rel=1e-6
    )


def test_ngspice_dummy_parasitics_reduction(tmp_path: Path) -> None:
    """Dummy switch should report 50% charge reduction via ngspice bench."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS_DUMMY)
    try:
        ng = simulate_parasitics_ngspice(cfg, tmp_path)
    except NgspiceNotFoundError:
        pytest.skip("ngspice not available")
    assert ng["charge"].dummy_reduction_pct == pytest.approx(50.0, abs=0.1)
