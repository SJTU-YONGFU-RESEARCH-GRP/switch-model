"""Cross-engine metric comparison for switch-model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_ENGINES = ("python", "ngspice", "spectre")
SWITCH_TYPES = ("nmos", "pmos", "cmos", "nmos_dummy", "bs", "bs_dummy")

TOLERANCE = {
    "ron_at_vcm_ohm": 0.02,
    "linearity_error_pct": 0.02,
    "flicker_corner_hz": 0.02,
    "noise_at_1hz_v_per_sqrt_hz": 0.02,
}


@dataclass(frozen=True)
class CompareResult:
    """Engine comparison outcome."""

    rows: list[dict[str, Any]]
    passed: bool
    engines_compared: tuple[str, ...]
    spectre_fallback: bool


def _load_metrics(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_value(metrics: dict[str, Any], key: str) -> float | None:
    parts = key.split(".")
    node: Any = metrics
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    if node is None or (isinstance(node, float) and node != node):
        return None
    return float(node)


def spectre_in_fallback_mode(output_root: Path) -> bool:
    """Return True when every Spectre switch run fell back to Python."""
    spectre_dir = output_root / "spectre"
    if not spectre_dir.is_dir():
        return True
    for stype in SWITCH_TYPES:
        fallback = spectre_dir / stype / "logs" / "spectre_ron_fallback.log"
        if not fallback.is_file():
            return False
    return True


def active_engines(
    output_root: Path,
    engines: tuple[str, ...] = DEFAULT_ENGINES,
) -> tuple[str, ...]:
    """Return engines to include in pass/fail comparison."""
    if "spectre" in engines and spectre_in_fallback_mode(output_root):
        return tuple(e for e in engines if e != "spectre")
    return engines


def compare_engines(
    output_root: Path,
    *,
    engines: tuple[str, ...] = DEFAULT_ENGINES,
    switch_types: tuple[str, ...] = SWITCH_TYPES,
) -> CompareResult:
    """Compare per-switch metrics across simulation engines."""
    compare_engines_list = active_engines(output_root, engines)
    spectre_fb = spectre_in_fallback_mode(output_root)
    rows: list[dict[str, Any]] = []
    passed = True

    for stype in switch_types:
        metric_keys = (
            "ron.ron_at_vcm_ohm",
            "ron.linearity_error_pct",
            "noise.flicker_corner_hz",
            "noise.noise_at_1hz_v_per_sqrt_hz",
        )
        for metric_key in metric_keys:
            values: dict[str, float] = {}
            for engine in compare_engines_list:
                metrics_path = output_root / engine / stype / "switch_metrics.json"
                val = _metric_value(_load_metrics(metrics_path), metric_key)
                if val is not None:
                    values[engine] = val
            if len(values) < 2:
                continue
            vmin = min(values.values())
            vmax = max(values.values())
            span = vmax - vmin
            metric_tail = metric_key.split(".")[-1]
            # Constant-Ron switches report ~0 linearity; tiny Spectre numeric dust is not a spread.
            negligible = 1.0e-3 if metric_tail == "linearity_error_pct" else 1.0e-9
            if span <= negligible or vmax <= negligible:
                spread = 0.0
            elif vmax > 0.0:
                spread = span / vmax
            else:
                spread = 0.0
            tol = TOLERANCE.get(metric_key.split(".")[-1], 0.02)
            ok = spread <= tol
            passed = passed and ok
            rows.append(
                {
                    "switch_type": stype,
                    "metric": metric_key,
                    "values": values,
                    "spread_pct": 100.0 * spread,
                    "tolerance_pct": 100.0 * tol,
                    "passed": ok,
                }
            )
    return CompareResult(
        rows=rows,
        passed=passed,
        engines_compared=compare_engines_list,
        spectre_fallback=spectre_fb,
    )


def format_compare_table(result: CompareResult) -> str:
    """Render comparison rows as a text table."""
    engine_label = " / ".join(result.engines_compared)
    lines = [
        f"Engine comparison ({engine_label})",
        "",
    ]
    if result.spectre_fallback:
        lines.append(
            "Note: spectre excluded — all runs fell back to Python (license/PSF)."
        )
        lines.append("")
    lines.extend(
        [
            f"{'Switch':<12} {'Metric':<28} {'Spread %':>10} {'Tol %':>8} {'OK':>4}",
            "-" * 70,
        ]
    )
    for row in result.rows:
        lines.append(
            f"{row['switch_type']:<12} {row['metric']:<28} "
            f"{row['spread_pct']:10.2f} {row['tolerance_pct']:8.1f} "
            f"{'yes' if row['passed'] else 'NO':>4}"
        )
        for engine, val in row["values"].items():
            lines.append(f"    {engine}: {val:.6g}")
    lines.append("")
    lines.append("PASS" if result.passed else "FAIL (spread exceeds tolerance)")
    return "\n".join(lines)
