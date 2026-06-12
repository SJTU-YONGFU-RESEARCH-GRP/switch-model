"""Tests for charge injection and clock feedthrough."""

from __future__ import annotations

from dataclasses import replace

import pytest

from switch_model.config import SwitchConfig, SwitchType
from switch_model.parasitics import charge_injection, clock_feedthrough


@pytest.mark.parametrize(
    ("base_type", "dummy_type"),
    [
        (SwitchType.NMOS, SwitchType.NMOS_DUMMY),
        (SwitchType.PMOS, SwitchType.PMOS_DUMMY),
        (SwitchType.CMOS, SwitchType.CMOS_DUMMY),
    ],
)
def test_dummy_reduces_charge_injection(
    base_type: SwitchType,
    dummy_type: SwitchType,
) -> None:
    """Dummy switch should reduce total injected charge versus plain switch."""
    base = SwitchConfig(switch_type=base_type)
    dummy = replace(base, switch_type=dummy_type)
    q_base = charge_injection(base).q_inj_coulomb
    q_dummy = charge_injection(dummy).q_inj_coulomb
    assert q_dummy < q_base
    assert charge_injection(dummy).dummy_reduction_pct > 0.0


def test_clock_feedthrough_scales_with_cgd() -> None:
    """Larger Cgd should increase clock feedthrough."""
    cfg_small = SwitchConfig(cgd_f=25.0e-15)
    cfg_large = replace(cfg_small, cgd_f=100.0e-15)
    v_small = clock_feedthrough(cfg_small).v_feedthrough_v
    v_large = clock_feedthrough(cfg_large).v_feedthrough_v
    assert v_large > v_small
