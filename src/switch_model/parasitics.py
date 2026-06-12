"""Charge injection and clock feedthrough models."""

from __future__ import annotations

from dataclasses import dataclass

from switch_model.config import SwitchConfig, SwitchType


@dataclass(frozen=True)
class ChargeInjectionMetrics:
    """Charge injection from channel and overlap capacitors."""

    q_inj_coulomb: float
    v_inj_v: float
    cgs_contribution_c: float
    cgd_contribution_c: float
    dummy_reduction_pct: float


@dataclass(frozen=True)
class ClockFeedthroughMetrics:
    """Clock feedthrough via gate-drain overlap capacitance."""

    v_feedthrough_v: float
    cgd_f: float
    c_load_f: float
    attenuation_db: float


def _delta_vclk(cfg: SwitchConfig) -> float:
    return cfg.vclk_high_v - cfg.vclk_low_v


def charge_injection(cfg: SwitchConfig) -> ChargeInjectionMetrics:
    """Estimate charge injection on switch turn-off (paper Fig. 1 parasitics)."""
    dv = _delta_vclk(cfg)
    cgs = cfg.cgs_f
    cgd = cfg.cgd_f
    split = cfg.dummy_charge_split
    q_no_dummy = (cgs + cgd) * dv
    if cfg.switch_type in (
        SwitchType.NMOS_DUMMY,
        SwitchType.PMOS_DUMMY,
        SwitchType.CMOS_DUMMY,
        SwitchType.BS_DUMMY,
    ):
        # Dummy steers a fraction of channel charge away from the signal node.
        q_total = q_no_dummy * (1.0 - split)
        reduction = 100.0 * split if q_no_dummy > 0.0 else 0.0
    else:
        q_total = q_no_dummy
        reduction = 0.0
    c_equiv = cgs + cgd + cfg.c_load_f
    v_inj = q_total / c_equiv if c_equiv > 0.0 else 0.0
    return ChargeInjectionMetrics(
        q_inj_coulomb=q_total,
        v_inj_v=v_inj,
        cgs_contribution_c=cgs * dv,
        cgd_contribution_c=cgd * dv,
        dummy_reduction_pct=reduction,
    )


def clock_feedthrough(cfg: SwitchConfig) -> ClockFeedthroughMetrics:
    """Estimate clock feedthrough through Cgd overlap (paper Fig. 1)."""
    caps = cfg.effective_parasitic_caps()
    cgd = caps["cgd_f"]
    c_load = cfg.c_load_f + caps["cp1_f"] + caps["cp2_f"]
    dv = _delta_vclk(cfg)
    v_cf = cgd * dv / (cgd + c_load) if (cgd + c_load) > 0.0 else 0.0
    attenuation = 20.0 * __import__("math").log10(cgd / (cgd + c_load)) if c_load > 0.0 else 0.0
    return ClockFeedthroughMetrics(
        v_feedthrough_v=v_cf,
        cgd_f=cgd,
        c_load_f=c_load,
        attenuation_db=attenuation,
    )
