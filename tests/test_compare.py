"""Tests for cross-engine comparison helpers."""

from __future__ import annotations

from pathlib import Path

import json

from switch_model.compare import TOLERANCE, active_engines, compare_engines, spectre_in_fallback_mode


def test_spectre_fallback_detection(tmp_path: Path) -> None:
    """Detect when all Spectre runs used Python fallback."""
    spectre = tmp_path / "spectre" / "nmos" / "logs"
    spectre.mkdir(parents=True)
    assert not spectre_in_fallback_mode(tmp_path)
    (spectre / "spectre_ron_fallback.log").write_text("fallback\n", encoding="utf-8")
    assert not spectre_in_fallback_mode(tmp_path)
    for stype in (
        "pmos",
        "cmos",
        "nmos_dummy",
        "pmos_dummy",
        "cmos_dummy",
        "bs",
        "bs_dummy",
    ):
        d = tmp_path / "spectre" / stype / "logs"
        d.mkdir(parents=True)
        (d / "spectre_ron_fallback.log").write_text("fallback\n", encoding="utf-8")
    assert spectre_in_fallback_mode(tmp_path)
    engines = active_engines(tmp_path)
    assert "spectre" not in engines
    assert "python" in engines and "ngspice" in engines


def test_compare_engines_uses_two_percent_tolerance(tmp_path: Path) -> None:
    """Cross-engine comparison should include noise @ 1 Hz at 2% tolerance."""
    engines = ("python", "ngspice")
    for engine in engines:
        metrics = {
            "ron": {"ron_at_vcm_ohm": 1000.0, "linearity_error_pct": 0.0},
            "noise": {
                "flicker_corner_hz": 100.0,
                "noise_at_1hz_v_per_sqrt_hz": 5.0e-8,
            },
        }
        path = tmp_path / engine / "nmos" / "switch_metrics.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(metrics), encoding="utf-8")

    result = compare_engines(tmp_path, engines=engines, switch_types=("nmos",))
    assert result.passed
    metrics_checked = {row["metric"] for row in result.rows}
    assert "noise.noise_at_1hz_v_per_sqrt_hz" in metrics_checked
    assert TOLERANCE["noise_at_1hz_v_per_sqrt_hz"] == 0.02
    assert TOLERANCE["flicker_corner_hz"] == 0.02
