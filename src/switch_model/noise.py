"""Channel thermal and flicker noise for MOS switches."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from switch_model.config import SwitchConfig, SwitchNoiseConfig
from switch_model.netlist import drive_voltages
from switch_model.ron import switch_ron

_K_BOLTZMANN = 1.380649e-23


def channel_current_a(v_in: float, v_out: float, ron_ohm: float) -> float:
    """Return channel current through the switch on-resistance."""
    if ron_ohm >= 1.0e11:
        return 0.0
    return (v_in - v_out) / ron_ohm


def flicker_power_at_1hz(noise: SwitchNoiseConfig, current_a: float) -> float:
    """Return flicker noise power at 1 Hz (A²/Hz or V²/Hz basis)."""
    if noise.kf > 0.0 and abs(current_a) > 0.0:
        return noise.kf * abs(current_a) ** noise.af
    en = noise.en_flicker_1hz_v_per_sqrt_hz
    return en * en if en > 0.0 else 0.0


def thermal_voltage_density(ron_ohm: float, noise: SwitchNoiseConfig) -> float:
    """Return thermal noise voltage density (V/√Hz) from channel resistance."""
    if noise.en_white_v_per_sqrt_hz > 0.0:
        return noise.en_white_v_per_sqrt_hz
    if ron_ohm <= 0.0 or ron_ohm >= 1.0e11:
        return 0.0
    return math.sqrt(4.0 * _K_BOLTZMANN * noise.temperature_k * ron_ohm)


def flicker_voltage_density(
    frequency_hz: NDArray[np.float64] | float,
    noise: SwitchNoiseConfig,
    current_a: float,
    ron_ohm: float,
) -> NDArray[np.float64]:
    """Return flicker noise voltage density (V/√Hz)."""
    pwr_1hz = flicker_power_at_1hz(noise, current_a)
    if pwr_1hz <= 0.0 or noise.en_flicker_ef <= 0.0:
        f = np.asarray(frequency_hz, dtype=np.float64)
        return np.zeros_like(f)
    f = np.maximum(np.asarray(frequency_hz, dtype=np.float64), 1.0e-30)
    if noise.kf > 0.0 and abs(current_a) > 0.0:
        vn = np.sqrt(pwr_1hz / f ** noise.en_flicker_ef)
        return vn.astype(np.float64)
    en_1hz = noise.en_flicker_1hz_v_per_sqrt_hz
    return (en_1hz / f ** (noise.en_flicker_ef / 2.0)).astype(np.float64)


def channel_noise_density(
    frequency_hz: NDArray[np.float64],
    cfg: SwitchConfig,
    *,
    v_in: float = 0.9,
    v_out: float = 0.9,
    vclk_v: float | None = None,
) -> NDArray[np.float64]:
    """Return total channel noise voltage density (V/√Hz) when switch is on."""
    noise = cfg.noise
    if not noise.enable_noise:
        return np.zeros_like(frequency_hz, dtype=np.float64)
    clk, _ = drive_voltages(cfg)
    if vclk_v is not None:
        clk = vclk_v
    ron = switch_ron(v_in, clk, cfg)
    current = channel_current_a(v_in, v_out, ron)
    thermal = thermal_voltage_density(ron, noise)
    flicker = flicker_voltage_density(frequency_hz, noise, current, ron)
    return np.sqrt(thermal**2 + flicker**2).astype(np.float64)


def flicker_corner_hz(cfg: SwitchConfig, *, v_in: float = 0.9, v_out: float = 0.9) -> float:
    """Return flicker corner where thermal and flicker densities are equal."""
    noise = cfg.noise
    clk, _ = drive_voltages(cfg)
    ron = switch_ron(v_in, clk, cfg)
    current = channel_current_a(v_in, v_out, ron)
    white = thermal_voltage_density(ron, noise)
    en_1hz = math.sqrt(flicker_power_at_1hz(noise, current))
    if white <= 0.0 or en_1hz <= 0.0 or noise.en_flicker_ef <= 0.0:
        return float("nan")
    return float((en_1hz / white) ** (2.0 / noise.en_flicker_ef))
