"""ngspice noise bench tests (skip when ngspice is not installed)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from switch_model.config import SwitchConfig, SwitchType
from switch_model.io import package_root
from switch_model.model import simulate_noise
from switch_model.ngspice_engine import (
    NgspiceNotFoundError,
    render_ngspice_noise_netlist,
    simulate_noise_ngspice,
)

pytestmark = pytest.mark.skipif(
    __import__("shutil").which("ngspice") is None
    and __import__("shutil").which("ngspice-shared") is None,
    reason="ngspice not on PATH",
)


def test_render_noise_netlist_has_noise_and_ac() -> None:
    """Rendered noise netlist includes .noise, .ac, and channel resistor."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    template = package_root() / "testbench" / "ngspice" / "noise_sweep.cir"
    text = render_ngspice_noise_netlist(template, cfg)
    assert ".noise V(out)" in text
    assert ".ac dec" in text
    assert "Rsw in out" in text
    assert "let flicker =" in text
    assert "wrdata noise_spectrum.raw frequency total" in text
    assert "PLACEHOLDER_" not in text


def test_ngspice_noise_matches_python(tmp_path: Path) -> None:
    """ngspice noise spectrum should track Python macromodel within tolerance."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    py = simulate_noise(cfg)
    try:
        ng = simulate_noise_ngspice(cfg, tmp_path)
    except NgspiceNotFoundError:
        pytest.skip("ngspice not available")
    assert (tmp_path / "logs" / "ngspice_engine_status.json").is_file()
    assert not (tmp_path / "logs" / "ngspice_noise_fallback.log").is_file()
    ng_interp = np.interp(py["frequency_hz"], ng["frequency_hz"], ng["noise_v_per_sqrt_hz"])
    rel = np.abs(py["noise_v_per_sqrt_hz"] - ng_interp) / np.maximum(py["noise_v_per_sqrt_hz"], 1.0e-30)
    assert float(rel.max()) < 0.05
