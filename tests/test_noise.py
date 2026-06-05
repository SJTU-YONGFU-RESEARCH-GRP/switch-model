"""Tests for channel noise models."""

from __future__ import annotations

import numpy as np
import pytest

from switch_model.config import SwitchConfig, SwitchNoiseConfig
from switch_model.io import log_frequency_sweep
from switch_model.noise import (
    channel_noise_density,
    flicker_corner_from_spectrum,
    flicker_corner_hz,
    thermal_voltage_density,
)


def test_thermal_from_ron() -> None:
    """Thermal noise should be derived from Ron when white level is zero."""
    noise = SwitchNoiseConfig(en_white_v_per_sqrt_hz=0.0)
    en = thermal_voltage_density(200.0, noise)
    assert en > 0.0


def test_flicker_dominates_at_low_frequency() -> None:
    """Flicker noise should exceed white at 1 Hz for default config."""
    cfg = SwitchConfig()
    f = log_frequency_sweep(1.0, 1.0e6, 10)
    spectrum = channel_noise_density(f, cfg)
    assert spectrum[0] >= spectrum[-1]


def test_flicker_corner_finite() -> None:
    """Flicker corner should be a positive finite value."""
    cfg = SwitchConfig()
    fc = flicker_corner_hz(cfg)
    assert fc > 0.0
    assert np.isfinite(fc)


def test_flicker_corner_from_spectrum_matches_analytic() -> None:
    """Spectrum-derived corner should track the analytic macromodel."""
    cfg = SwitchConfig()
    f = log_frequency_sweep(1.0, 1.0e6, 10)
    spectrum = channel_noise_density(f, cfg)
    fc_spectrum = flicker_corner_from_spectrum(f, spectrum, cfg=cfg)
    fc_analytic = flicker_corner_hz(cfg)
    assert np.isfinite(fc_spectrum)
    assert fc_spectrum == pytest.approx(fc_analytic, rel=0.05)
