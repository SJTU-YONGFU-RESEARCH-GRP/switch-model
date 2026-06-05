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


def _leg_noise_spectrum(
    frequency_hz: NDArray[np.float64],
    noise: SwitchNoiseConfig,
    *,
    ron_ohm: float,
    current_a: float,
) -> NDArray[np.float64]:
    """Return per-leg channel noise voltage density (V/√Hz)."""
    thermal = thermal_voltage_density(ron_ohm, noise)
    flicker = flicker_voltage_density(frequency_hz, noise, current_a, ron_ohm)
    return np.sqrt(thermal**2 + flicker**2).astype(np.float64)


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
    return _leg_noise_spectrum(
        frequency_hz,
        noise,
        ron_ohm=ron,
        current_a=channel_current_a(v_in, v_out, ron),
    )


def thermal_noise_floor(cfg: SwitchConfig, *, v_in: float | None = None) -> float:
    """Return thermal noise floor (V/√Hz) at VCM for spectrum corner extraction."""
    vcm = 0.5 * (cfg.vdd_v + cfg.vss_v) if v_in is None else v_in
    vclk, _ = drive_voltages(cfg)
    ron = switch_ron(vcm, vclk, cfg)
    return thermal_voltage_density(ron, cfg.noise)


def flicker_corner_from_spectrum(
    frequency_hz: NDArray[np.float64],
    noise_v_per_sqrt_hz: NDArray[np.float64],
    *,
    cfg: SwitchConfig | None = None,
) -> float:
    """Estimate flicker corner (Hz) from a simulated noise spectrum.

    When ``cfg`` is provided, anchors the corner to the simulated density at
    1 Hz (first sweep point) and the macromodel thermal floor at VCM, using
    the configured ``1/f`` exponent. This matches analytic corners when the
    simulated 1 Hz level agrees across engines.

    Without ``cfg``, falls back to locating the thermal crossing on the full
    spectrum using the high-frequency noise floor.
    """
    vn = np.asarray(noise_v_per_sqrt_hz, dtype=np.float64)
    if vn.size < 1 or not np.all(np.isfinite(vn)):
        return float("nan")
    if cfg is not None:
        white = thermal_noise_floor(cfg)
        flicker_1hz = float(np.sqrt(np.maximum(vn[0] ** 2 - white**2, 0.0)))
        ef = cfg.noise.en_flicker_ef
        if white <= 0.0 or flicker_1hz <= 0.0 or ef <= 0.0:
            return float("nan")
        return float((flicker_1hz / white) ** (2.0 / ef))

    f = np.asarray(frequency_hz, dtype=np.float64)
    if vn.size < 3:
        return float("nan")
    n_hi = max(3, int(0.2 * vn.size))
    white = float(np.median(vn[-n_hi:]))
    if white <= 0.0:
        return float("nan")
    flicker = np.sqrt(np.maximum(vn**2 - white**2, 0.0))
    if not np.any(flicker > white):
        return float("nan")
    for idx in range(1, flicker.size):
        if flicker[idx - 1] > white >= flicker[idx]:
            f0, f1 = float(f[idx - 1]), float(f[idx])
            v0, v1 = float(flicker[idx - 1]), float(flicker[idx])
            if abs(v1 - v0) < 1.0e-30:
                return f1
            frac = (white - v0) / (v1 - v0)
            frac = min(max(frac, 0.0), 1.0)
            return f0 + frac * (f1 - f0)
    return float(f[-1])


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
