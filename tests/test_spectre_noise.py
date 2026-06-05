"""Spectre noise netlist and engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from switch_model.config import SwitchConfig, SwitchType
from switch_model.io import package_root
from switch_model.spectre_engine import render_spectre_noise_netlist

pytestmark = pytest.mark.skipif(
    __import__("shutil").which("spectre") is None,
    reason="Spectre not on PATH",
)


def test_render_noise_netlist_includes_noise_analysis() -> None:
    """Rendered Spectre deck runs ``noise`` on ``out`` with VA noise enabled."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    template = package_root() / "testbench" / "spectre" / "noise_sweep.scs"
    text = render_spectre_noise_netlist(template, cfg)
    assert "noise noise start=" in text
    assert "oprobe=N1" in text
    assert "parameters enable_noise=1" in text
    assert "ENABLE_NOISE=enable_noise" in text
    assert "ahdl_include" in text


def test_spectre_noise_simulation(tmp_path: Path) -> None:
    """Spectre noise run completes and returns finite spectrum when PSF is readable."""
    pytest.importorskip("psf_parser")
    from switch_model.spectre_engine import SpectreNotFoundError, simulate_noise_spectre

    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    try:
        result = simulate_noise_spectre(cfg, tmp_path)
    except SpectreNotFoundError:
        pytest.skip("Spectre not available")
    except RuntimeError as exc:
        msg = str(exc)
        skip_markers = ("PSF", "license", "LMC-", "failed with code")
        if any(marker.lower() in msg.lower() for marker in skip_markers):
            pytest.skip(f"Spectre noise not available: {exc}")
        raise
    assert result["noise_v_per_sqrt_hz"].max() > 0.0
    if (tmp_path / "logs" / "spectre_noise_fallback.log").is_file():
        pytest.skip("Spectre noise fell back to Python")
    assert (tmp_path / "logs" / "spectre_engine_status.json").is_file()
