"""Tests for Spectre PSF Ron extraction."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from switch_model.config import SwitchConfig, SwitchType
from switch_model.ron import nmos_ron, ron_vs_vin
from switch_model.spectre_psf import _ron_from_psf_traces, read_spectre_dc_ron


def test_ron_from_psf_traces_falls_back_at_zero_current() -> None:
    """Vin=0 with zero PSF current should use analytic Ron, not ROFF."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    vin = np.array([0.0, 0.1], dtype=np.float64)
    vout = np.array([0.0, 0.1], dtype=np.float64)
    i_vin = np.array([0.0, 1.0e-6], dtype=np.float64)
    expected_zero = nmos_ron(0.0, cfg.vclk_high_v, cfg)

    ron = _ron_from_psf_traces(vin, vout=vout, i_vin=i_vin, cfg=cfg)

    assert ron[0] == pytest.approx(expected_zero)
    assert ron[0] < cfg.roff_ohm * 0.5
    assert ron[1] == pytest.approx(0.1 / 1.0e-6)


def test_ron_from_psf_traces_falls_back_without_vin_current() -> None:
    """When Vin:p is absent, zero Vout should still yield analytic Ron."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    vin = np.array([0.0, 0.2], dtype=np.float64)
    vout = np.array([0.0, 0.2], dtype=np.float64)
    analytic = ron_vs_vin(vin, cfg)

    ron = _ron_from_psf_traces(vin, vout=vout, i_vin=None, cfg=cfg)

    assert ron[0] == pytest.approx(analytic[0])
    assert ron[0] < cfg.roff_ohm * 0.5


@pytest.mark.parametrize("switch_type", [SwitchType.NMOS, SwitchType.CMOS])
def test_read_spectre_dc_ron_vin_zero_not_roff(switch_type: SwitchType) -> None:
    """Recorded Spectre PSF sweeps should not report ROFF at Vin=0."""
    psf_dir = Path(f"outputs/spectre/{switch_type.value}/logs/netlists/ron_sweep.raw")
    if not psf_dir.is_dir():
        pytest.skip(f"PSF fixture not found: {psf_dir}")

    cfg = SwitchConfig(switch_type=switch_type)
    result = read_spectre_dc_ron(psf_dir, cfg)
    analytic = ron_vs_vin(result["vin_v"], cfg)

    assert result["ron_ohm"][0] < cfg.roff_ohm * 0.5
    assert result["ron_ohm"][0] == pytest.approx(analytic[0])
    assert result["metrics"].ron_min_ohm == pytest.approx(analytic[0])
