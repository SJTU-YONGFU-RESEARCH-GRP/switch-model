"""Spectre parasitics bench tests (skip when Spectre is not installed)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from switch_model.config import SwitchConfig, SwitchType
from switch_model.io import package_root
from switch_model.model import simulate_parasitics
from switch_model.spectre_engine import (
    SpectreNotFoundError,
    render_spectre_parasitics_netlist,
    simulate_parasitics_spectre,
)
from switch_model.spectre_psf import read_spectre_parasitics_psf

pytestmark = pytest.mark.skipif(
    __import__("shutil").which("spectre") is None
    and not Path("/eda/cadence/SPECTRE241/tools/bin/spectre").is_file(),
    reason="Spectre not on PATH",
)


def test_render_parasitics_netlist_has_probe_nodes() -> None:
    """Rendered parasitics netlist embeds charge and feedthrough literals."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS_DUMMY)
    template = package_root() / "testbench" / "spectre" / "parasitics_bench.scs"
    text = render_spectre_parasitics_netlist(template, cfg)
    assert "save mq mv mcf matt md" in text
    assert "PLACEHOLDER_" not in text
    assert "dummy_reduction_pct" in text


def test_read_spectre_parasitics_psf_reads_scalar_values(tmp_path: Path) -> None:
    """Scalar DC PSF nodes convert to parasitic metrics."""
    values = [
        SimpleNamespace(name="mq", data=9.0e-5),
        SimpleNamespace(name="mv", data=0.08571428571428573),
        SimpleNamespace(name="mcf", data=0.041860465116279076),
        SimpleNamespace(name="matt", data=-32.66936911159173),
        SimpleNamespace(name="md", data=50.0),
    ]
    registry = SimpleNamespace(values=values, traces=[])

    psf_dir = tmp_path / "parasitics_bench.raw"
    psf_dir.mkdir()
    with patch("switch_model.spectre_psf.resolve_dc_psf_path", return_value=Path("dcOp.dc")):
        with patch("switch_model.spectre_psf._load_psf_registry", return_value=registry):
            parsed = read_spectre_parasitics_psf(psf_dir)

    assert parsed["q_inj_coulomb"] == pytest.approx(9.0e-14, rel=1.0e-6)
    assert parsed["v_inj_v"] == pytest.approx(0.08571428571428573, rel=1.0e-6)
    assert parsed["dummy_reduction_pct"] == pytest.approx(50.0, abs=0.1)


def test_spectre_parasitics_matches_python(tmp_path: Path) -> None:
    """Spectre parasitics metrics should match Python macromodel."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS)
    py = simulate_parasitics(cfg)
    try:
        sp = simulate_parasitics_spectre(cfg, tmp_path)
    except SpectreNotFoundError:
        pytest.skip("Spectre not available")
    assert not (tmp_path / "logs" / "spectre_parasitics_fallback.log").is_file()
    assert py["charge"].q_inj_coulomb == pytest.approx(sp["charge"].q_inj_coulomb, rel=1e-6)
    assert py["charge"].v_inj_v == pytest.approx(sp["charge"].v_inj_v, rel=1e-6)
    assert py["feedthrough"].v_feedthrough_v == pytest.approx(
        sp["feedthrough"].v_feedthrough_v, rel=1e-6
    )
    assert py["feedthrough"].attenuation_db == pytest.approx(
        sp["feedthrough"].attenuation_db, rel=1e-6
    )


def test_spectre_dummy_parasitics_reduction(tmp_path: Path) -> None:
    """Dummy switch should report 50% charge reduction via Spectre bench."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS_DUMMY)
    try:
        sp = simulate_parasitics_spectre(cfg, tmp_path)
    except SpectreNotFoundError:
        pytest.skip("Spectre not available")
    assert sp["charge"].dummy_reduction_pct == pytest.approx(50.0, abs=0.1)
