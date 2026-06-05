"""Tests for bench plotting helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from switch_model.config import SwitchConfig, SwitchType
from switch_model.model import simulate_parasitics
from switch_model.plotting import plot_parasitics_summary


def test_plot_parasitics_summary_writes_svg(tmp_path: Path) -> None:
    """Parasitics bar chart should be saved as SVG."""
    cfg = SwitchConfig(switch_type=SwitchType.NMOS_DUMMY)
    result = simulate_parasitics(cfg)
    out = tmp_path / "parasitics_summary.svg"
    plot_parasitics_summary(
        result["charge"],
        result["feedthrough"],
        out,
        title="Parasitics",
        switch_type=cfg.switch_type.value,
    )
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "<svg" in text
