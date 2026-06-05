"""Integration tests across switch topologies."""

from __future__ import annotations

from dataclasses import replace

import pytest

from switch_model.config import SwitchConfig, SwitchType
from switch_model.model import simulate_noise, simulate_parasitics, simulate_ron_sweep


@pytest.mark.parametrize("stype", list(SwitchType))
def test_all_switch_types_simulate(stype: SwitchType) -> None:
    """Each switch type should run Ron, noise, and parasitic benches."""
    cfg = replace(SwitchConfig(), switch_type=stype)
    ron = simulate_ron_sweep(cfg)
    noise = simulate_noise(cfg)
    parasitics = simulate_parasitics(cfg)
    assert ron["metrics"].ron_min_ohm > 0.0
    assert len(noise["frequency_hz"]) > 1
    assert parasitics["charge"].q_inj_coulomb > 0.0
