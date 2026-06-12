"""Verify Verilog-A module files exist and reference paper."""

from __future__ import annotations

from switch_model.io import package_root


def test_veriloga_modules_exist() -> None:
    """All switch Verilog-A wrappers should be present."""
    va_dir = package_root() / "veriloga"
    expected = [
        "configurable_switch.va",
        "configurable_nmos_switch.va",
        "configurable_pmos_switch.va",
        "configurable_cmos_switch.va",
        "configurable_nmos_dummy_switch.va",
        "configurable_pmos_dummy_switch.va",
        "configurable_cmos_dummy_switch.va",
        "configurable_bs_switch.va",
        "configurable_bs_dummy_switch.va",
    ]
    for name in expected:
        assert (va_dir / name).is_file(), f"Missing {name}"


def test_base_va_cites_paper() -> None:
    """Base switch VA should cite Zhou et al. NEWCAS 2021."""
    text = (package_root() / "veriloga" / "configurable_switch.va").read_text(encoding="utf-8")
    assert "NEWCAS 2021" in text
    assert "flicker_noise" in text
