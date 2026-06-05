"""Simulation orchestration entry points."""

from __future__ import annotations

from typing import TypedDict

import numpy as np
from numpy.typing import NDArray

from switch_model.config import SwitchConfig
from switch_model.io import linear_voltage_sweep, log_frequency_sweep
from switch_model.noise import channel_noise_density, flicker_corner_hz
from switch_model.parasitics import (
    ChargeInjectionMetrics,
    ClockFeedthroughMetrics,
    charge_injection,
    clock_feedthrough,
)
from switch_model.ron import RonMetrics, extract_ron_metrics, ron_vs_vin


class RonSimulationResult(TypedDict):
    """Ron sweep result bundle."""

    vin_v: NDArray[np.float64]
    ron_ohm: NDArray[np.float64]
    metrics: RonMetrics


class NoiseSimulationResult(TypedDict):
    """Noise spectrum result bundle."""

    frequency_hz: NDArray[np.float64]
    noise_v_per_sqrt_hz: NDArray[np.float64]
    flicker_corner_hz: float


class ParasiticSimulationResult(TypedDict):
    """Charge injection and clock feedthrough metrics."""

    charge: ChargeInjectionMetrics
    feedthrough: ClockFeedthroughMetrics


def simulate_ron_sweep(cfg: SwitchConfig) -> RonSimulationResult:
    """Run Ron versus Vin sweep for the configured switch."""
    vin = linear_voltage_sweep(
        cfg.sweep.vin_start_v,
        cfg.sweep.vin_stop_v,
        cfg.sweep.vin_points,
    )
    ron = ron_vs_vin(vin, cfg)
    metrics = extract_ron_metrics(vin, ron, cfg)
    return RonSimulationResult(vin_v=vin, ron_ohm=ron, metrics=metrics)


def simulate_noise(cfg: SwitchConfig) -> NoiseSimulationResult:
    """Run channel noise spectrum when the switch is on."""
    f = log_frequency_sweep(
        cfg.sweep.f_start_hz,
        cfg.sweep.f_stop_hz,
        cfg.sweep.points_per_decade,
    )
    vcm = 0.5 * (cfg.vdd_v + cfg.vss_v)
    spectrum = channel_noise_density(f, cfg, v_in=vcm, v_out=vcm)
    return NoiseSimulationResult(
        frequency_hz=f,
        noise_v_per_sqrt_hz=spectrum,
        flicker_corner_hz=flicker_corner_hz(cfg, v_in=vcm, v_out=vcm),
    )


def simulate_charge_injection(cfg: SwitchConfig) -> ChargeInjectionMetrics:
    """Return charge injection metrics for the configured switch."""
    return charge_injection(cfg)


def simulate_clock_feedthrough(cfg: SwitchConfig) -> ClockFeedthroughMetrics:
    """Return clock feedthrough metrics for the configured switch."""
    return clock_feedthrough(cfg)


def simulate_parasitics(cfg: SwitchConfig) -> ParasiticSimulationResult:
    """Return charge injection and clock feedthrough together."""
    return ParasiticSimulationResult(
        charge=charge_injection(cfg),
        feedthrough=clock_feedthrough(cfg),
    )
