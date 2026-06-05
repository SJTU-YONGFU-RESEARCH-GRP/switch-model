"""Unit tests for Spectre noise PSF parsing (mocked registry)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from switch_model.config import SwitchConfig
from switch_model.noise import thermal_noise_floor
from switch_model.spectre_psf import SpectrePsfError, read_spectre_noise_psf


def test_read_spectre_noise_psf_reads_structured_rload_trace() -> None:
    """Noise PSF reader extracts ``total`` density from structured Rload traces."""
    sweep = SimpleNamespace(data=[1.0, 10.0, 100.0])
    traces = [
        SimpleNamespace(
            name="Rload",
            data=[
                {"rn": 1.0e-8, "total": 1.1e-8},
                {"rn": 5.0e-9, "total": 5.5e-9},
                {"rn": 2.0e-9, "total": 2.2e-9},
            ],
        ),
        SimpleNamespace(name="out", data=[5.0, 4.0, 3.0]),
    ]
    registry = SimpleNamespace(sweeps=[sweep], traces=traces)

    with patch("switch_model.spectre_psf._load_psf_registry", return_value=registry):
        parsed = read_spectre_noise_psf(Path("noise.psf"), signal="Rload")

    assert np.allclose(parsed["frequency_hz"], [1.0, 10.0, 100.0])
    assert parsed["noise_v_per_sqrt_hz"][0] == pytest.approx(1.1e-8)


def test_read_spectre_noise_psf_combines_n1_flicker_and_thermal() -> None:
    """N1 traces combine scaled flicker with a constant thermal floor."""
    sweep = SimpleNamespace(data=[1.0, 1000.0])
    traces = [
        SimpleNamespace(
            name="N1",
            data=[
                {"flicker": 24.0, "thermal": 1.6, "total": 26.0},
                {"flicker": 0.001, "thermal": 1.6, "total": 1.6e-8},
            ],
        ),
    ]
    registry = SimpleNamespace(sweeps=[sweep], traces=traces)

    with patch("switch_model.spectre_psf._load_psf_registry", return_value=registry):
        parsed = read_spectre_noise_psf(Path("noise.psf"), signal="N1")

    expected_1hz = np.sqrt((24.0e-9) ** 2 + (1.6e-8) ** 2)
    assert parsed["noise_v_per_sqrt_hz"][0] == pytest.approx(expected_1hz)
    assert parsed["noise_v_per_sqrt_hz"][1] == pytest.approx(1.6e-8, rel=1.0e-6)


def test_read_spectre_noise_psf_handles_va_flicker_power_units() -> None:
    """Large flicker powers from VA ``flicker_noise`` convert to V/√Hz."""
    sweep = SimpleNamespace(data=[1.0, 1000.0])
    power_at_1hz = 2.5e9
    traces = [
        SimpleNamespace(
            name="N1",
            data=[
                {"flicker": power_at_1hz, "thermal": 1.6, "total": power_at_1hz + 1.0},
                {"flicker": 1.0e-15, "thermal": 1.6e-8, "total": 1.6e-8},
            ],
        ),
    ]
    registry = SimpleNamespace(sweeps=[sweep], traces=traces)

    cfg = SwitchConfig()
    with patch("switch_model.spectre_psf._load_psf_registry", return_value=registry):
        parsed = read_spectre_noise_psf(Path("noise.psf"), signal="N1", cfg=cfg)

    white = thermal_noise_floor(cfg)
    expected_1hz = np.sqrt(cfg.noise.en_flicker_1hz_v_per_sqrt_hz**2 + white**2)
    assert parsed["noise_v_per_sqrt_hz"][0] == pytest.approx(expected_1hz)
    assert parsed["noise_v_per_sqrt_hz"][1] == pytest.approx(white, rel=1.0e-6)


def test_read_spectre_noise_psf_missing_sweep_raises() -> None:
    """Empty sweep should raise ``SpectrePsfError``."""
    registry = SimpleNamespace(sweeps=[], traces=[])
    with patch("switch_model.spectre_psf._load_psf_registry", return_value=registry):
        with pytest.raises(SpectrePsfError, match="No frequency sweep"):
            read_spectre_noise_psf(Path("noise.psf"))
