"""Tests for Ron models."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from switch_model.config import SwitchConfig, SwitchType
from switch_model.ron import bs_ron, cmos_ron, nmos_ron, ron_vs_vin, switch_ron


def test_nmos_ron_increases_with_vin() -> None:
    """NMOS Ron should rise as Vin approaches Vclk."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    r_low = nmos_ron(0.0, cfg.vclk_high_v, cfg)
    r_high = nmos_ron(1.0, cfg.vclk_high_v, cfg)
    assert r_high > r_low
    assert r_low < cfg.roff_ohm


def test_bs_ron_is_constant() -> None:
    """Bootstrapped switch Ron should be independent of Vin."""
    cfg = SwitchConfig(switch_type=SwitchType.BS)
    r1 = bs_ron(0.2, cfg.vclk_high_v, cfg)
    r2 = bs_ron(1.5, cfg.vclk_high_v, cfg)
    assert r1 == r2 == cfg.ron_bs_ohm


def test_cmos_ron_lower_than_nmos_alone() -> None:
    """Transmission gate Ron should be below NMOS-only at mid-rail."""
    from switch_model.netlist import drive_voltages

    cfg = SwitchConfig(switch_type=SwitchType.CMOS)
    vclk, _ = drive_voltages(cfg)
    v = 0.9
    r_n = switch_ron(v, vclk, replace(cfg, switch_type=SwitchType.NMOS))
    r_tg = cmos_ron(v, vclk, cfg)
    assert r_tg < r_n


def test_ron_sweep_shape() -> None:
    """Ron sweep should return finite on-state values below mid-rail Vin."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    vin = np.linspace(0.0, 1.0, 20)
    ron = ron_vs_vin(vin, cfg)
    assert np.all(np.isfinite(ron))
    assert np.all(ron < cfg.roff_ohm)
