"""Signal-dependent on-resistance models for MOS switches."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from switch_model.config import SwitchConfig, SwitchType


@dataclass(frozen=True)
class RonMetrics:
    """Scalar Ron metrics from a voltage sweep."""

    ron_min_ohm: float
    ron_max_ohm: float
    ron_at_vcm_ohm: float
    linearity_error_pct: float


def _parallel_resistance(r1: float, r2: float) -> float:
    if r1 >= 1.0e11 and r2 >= 1.0e11:
        return 1.0e12
    if r1 >= 1.0e11:
        return r2
    if r2 >= 1.0e11:
        return r1
    return (r1 * r2) / (r1 + r2)


def nmos_ron(v_in: float, v_clk: float, cfg: SwitchConfig) -> float:
    """Return NMOS on-resistance (paper Fig. 3: Ron = 1/(K*Ratio*(Vclk-Vin-Vth)))."""
    if v_clk <= cfg.vth_n_v:
        return cfg.roff_ohm
    vgs_eff = v_clk - v_in - cfg.vth_n_v
    if vgs_eff <= 1.0e-6:
        return cfg.roff_ohm
    return 1.0 / (cfg.k_n * cfg.ratio * vgs_eff)


def pmos_ron(v_in: float, v_clk: float, cfg: SwitchConfig) -> float:
    """Return PMOS on-resistance with source at ``in`` and gate at ``v_clk``."""
    vgs = v_clk - v_in
    if vgs >= cfg.vth_p_v:
        return cfg.roff_ohm
    vgs_eff = cfg.vth_p_v - vgs
    if vgs_eff <= 1.0e-6:
        return cfg.roff_ohm
    return 1.0 / (cfg.k_p * cfg.ratio * vgs_eff)


def bs_ron(_v_in: float, _v_clk: float, cfg: SwitchConfig) -> float:
    """Return bootstrapped switch on-resistance (constant Ron)."""
    if _v_clk <= cfg.vth_n_v:
        return cfg.roff_ohm
    return cfg.ron_bs_ohm


def cmos_ron(v_in: float, v_clk: float, cfg: SwitchConfig) -> float:
    """Return transmission-gate on-resistance (NMOS || PMOS)."""
    v_clk_bar = cfg.vdd_v - v_clk + cfg.vss_v
    r_n = nmos_ron(v_in, v_clk, cfg)
    r_p = pmos_ron(v_in, v_clk_bar, cfg)
    return _parallel_resistance(r_n, r_p)


def switch_ron(v_in: float, v_clk: float, cfg: SwitchConfig) -> float:
    """Return on-resistance for the configured switch topology."""
    match cfg.switch_type:
        case SwitchType.NMOS | SwitchType.NMOS_DUMMY:
            return nmos_ron(v_in, v_clk, cfg)
        case SwitchType.PMOS:
            return pmos_ron(v_in, v_clk, cfg)
        case SwitchType.CMOS:
            return cmos_ron(v_in, v_clk, cfg)
        case SwitchType.BS | SwitchType.BS_DUMMY:
            return bs_ron(v_in, v_clk, cfg)
        case _:
            msg = f"Unsupported switch type: {cfg.switch_type}"
            raise ValueError(msg)


def ron_vs_vin(
    vin_v: NDArray[np.float64],
    cfg: SwitchConfig,
    *,
    vclk_v: float | None = None,
) -> NDArray[np.float64]:
    """Sweep Ron versus input voltage with switch asserted on."""
    clk = cfg.vclk_high_v if vclk_v is None else vclk_v
    return np.array([switch_ron(float(v), clk, cfg) for v in vin_v], dtype=np.float64)


def extract_ron_metrics(
    vin_v: NDArray[np.float64],
    ron_ohm: NDArray[np.float64],
    cfg: SwitchConfig,
) -> RonMetrics:
    """Extract Ron min/max and linearity error relative to bootstrapped reference."""
    finite = ron_ohm[np.isfinite(ron_ohm) & (ron_ohm < cfg.roff_ohm * 0.5)]
    if finite.size == 0:
        return RonMetrics(
            ron_min_ohm=cfg.roff_ohm,
            ron_max_ohm=cfg.roff_ohm,
            ron_at_vcm_ohm=cfg.roff_ohm,
            linearity_error_pct=0.0,
        )
    vcm = 0.5 * (cfg.vdd_v + cfg.vss_v)
    idx = int(np.argmin(np.abs(vin_v - vcm)))
    r_min = float(np.min(finite))
    r_max = float(np.max(finite))
    r_vcm = float(ron_ohm[idx])
    ref = cfg.ron_bs_ohm if cfg.switch_type != SwitchType.BS else r_min
    linearity = 100.0 * (r_max - r_min) / ref if ref > 0.0 else 0.0
    return RonMetrics(
        ron_min_ohm=r_min,
        ron_max_ohm=r_max,
        ron_at_vcm_ohm=r_vcm,
        linearity_error_pct=linearity,
    )
