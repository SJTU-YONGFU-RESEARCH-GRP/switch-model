"""Tests for Markdown report generation."""

from __future__ import annotations

import json
from pathlib import Path

from switch_model.compare import CompareResult
from switch_model.report import (
    refresh_reports_after_bench,
    write_engine_comparison_report,
    write_summary_report,
    write_switch_type_report,
)


def test_write_switch_type_report(tmp_path: Path) -> None:
    """Per-switch REPORT.md should link bench reports and embed figures."""
    sub = tmp_path / "nmos"
    sub.mkdir()
    (sub / "RON_REPORT.md").write_text("# Ron\n", encoding="utf-8")
    (sub / "ron_sweep.svg").write_text("<svg></svg>", encoding="utf-8")
    (sub / "switch_metrics.json").write_text(
        json.dumps({"ron": {"ron_min_ohm": 100.0}}),
        encoding="utf-8",
    )
    path = write_switch_type_report(sub, switch_type="nmos")
    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert "Ron sweep" in text
    assert "ron_sweep.svg" in text


def test_write_summary_report(tmp_path: Path) -> None:
    """Top-level REPORT.md should include comparison table and gallery."""
    compare_dir = tmp_path / "compare"
    compare_dir.mkdir()
    (compare_dir / "switch_comparison.json").write_text(
        json.dumps(
            {
                "nmos": {
                    "ron": {"ron_at_vcm_ohm": 5000.0, "linearity_error_pct": 10.0},
                    "noise": {"flicker_corner_hz": 100.0},
                    "charge_injection": {"v_inj_v": 0.01},
                    "clock_feedthrough": {"v_feedthrough_v": 0.005},
                }
            }
        ),
        encoding="utf-8",
    )
    sub = tmp_path / "nmos"
    sub.mkdir()
    (sub / "RON_REPORT.md").write_text("# Ron\n", encoding="utf-8")
    (sub / "ron_sweep.svg").write_text("<svg></svg>", encoding="utf-8")
    write_switch_type_report(sub, switch_type="nmos")

    path = write_summary_report(tmp_path)
    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert "Switch comparison" in text
    assert "Figure gallery" in text
    assert "nmos/ron_sweep.svg" in text


def test_write_switch_type_report_includes_parasitics_figure(tmp_path: Path) -> None:
    """Per-switch REPORT.md should embed parasitics SVG when present."""
    sub = tmp_path / "nmos_dummy"
    sub.mkdir()
    (sub / "PARASITICS_REPORT.md").write_text("# Parasitics\n", encoding="utf-8")
    (sub / "parasitics_summary.svg").write_text("<svg></svg>", encoding="utf-8")
    path = write_switch_type_report(sub, switch_type="nmos_dummy")
    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert "parasitics_summary.svg" in text
    assert "Parasitics summary" in text


def test_refresh_reports_after_bench_updates_engine_summary(tmp_path: Path) -> None:
    """Bench refresh should regenerate per-switch and engine-level reports."""
    compare_dir = tmp_path / "compare"
    compare_dir.mkdir()
    (compare_dir / "switch_comparison.json").write_text(
        json.dumps({"nmos": {"ron": {"ron_at_vcm_ohm": 5000.0}}}),
        encoding="utf-8",
    )
    sub = tmp_path / "nmos"
    sub.mkdir()
    (sub / "RON_REPORT.md").write_text("# Ron\n", encoding="utf-8")
    (sub / "ron_sweep.svg").write_text("<svg></svg>", encoding="utf-8")

    written = refresh_reports_after_bench(sub, switch_type="nmos")
    paths = {p.name for p in written}
    assert "REPORT.md" in paths
    assert (sub / "REPORT.md").is_file()
    assert (tmp_path / "REPORT.md").is_file()


def test_write_engine_comparison_report_includes_gallery(tmp_path: Path) -> None:
    """Cross-engine REPORT.md should embed figures from each engine."""
    for engine in ("python", "ngspice"):
        sub = tmp_path / engine / "nmos"
        sub.mkdir(parents=True)
        (sub / "ron_sweep.svg").write_text("<svg></svg>", encoding="utf-8")

    result = CompareResult(
        rows=[],
        passed=True,
        engines_compared=("python", "ngspice"),
        spectre_fallback=True,
    )
    path = write_engine_comparison_report(tmp_path, result, engines=("python", "ngspice"))
    text = path.read_text(encoding="utf-8")
    assert "Figure gallery" in text
    assert "python/nmos/ron_sweep.svg" in text
    assert "ngspice/nmos/ron_sweep.svg" in text
