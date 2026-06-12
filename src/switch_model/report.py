"""Markdown report helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SWITCH_TYPES = (
    "nmos",
    "pmos",
    "cmos",
    "nmos_dummy",
    "pmos_dummy",
    "cmos_dummy",
    "bs",
    "bs_dummy",
)

PAPER_LABELS = {
    "nmos": "NS",
    "pmos": "PMOS",
    "cmos": "TG",
    "nmos_dummy": "NS-D",
    "pmos_dummy": "PMOS-D",
    "cmos_dummy": "TG-D",
    "bs": "BS",
    "bs_dummy": "BS+D",
}


def _utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp for report headers."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _figure_block(rel_path: str, caption: str) -> str:
    """Markdown image block using a path relative to the report file."""
    return f"![{caption}]({rel_path})\n\n*{caption}*\n"


def _fmt_float(value: float | None, *, unit: str = "") -> str:
    """Format a scalar for Markdown tables."""
    if value is None:
        return "—"
    if value != value:  # NaN
        return "N/A"
    if abs(value) >= 1.0e12:
        return f"{value:.3e}"
    suffix = f" {unit}" if unit else ""
    return f"{value:.4g}{suffix}"


def write_ron_report(
    path: Path,
    *,
    switch_type: str,
    ron_min_ohm: float,
    ron_max_ohm: float,
    linearity_error_pct: float,
    svg_name: str = "ron_sweep.svg",
) -> None:
    """Write Ron bench Markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"""# Ron sweep report — {switch_type}

| Metric | Value |
| --- | --- |
| Ron min | {ron_min_ohm:.2f} Ω |
| Ron max | {ron_max_ohm:.2f} Ω |
| Linearity error | {linearity_error_pct:.2f} % |

![Ron sweep]({svg_name})
"""
    path.write_text(body, encoding="utf-8")


def write_noise_report(
    path: Path,
    *,
    switch_type: str,
    flicker_corner_hz: float,
    svg_name: str = "noise_spectrum.svg",
) -> None:
    """Write noise bench Markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fc = f"{flicker_corner_hz:.2f} Hz" if flicker_corner_hz == flicker_corner_hz else "N/A"
    body = f"""# Noise spectrum report — {switch_type}

| Metric | Value |
| --- | --- |
| Flicker corner | {fc} |

![Noise spectrum]({svg_name})
"""
    path.write_text(body, encoding="utf-8")


def write_parasitics_report(
    path: Path,
    *,
    switch_type: str,
    q_inj_coulomb: float,
    v_inj_v: float,
    dummy_reduction_pct: float,
    v_feedthrough_v: float,
    attenuation_db: float,
    svg_name: str = "parasitics_summary.svg",
) -> None:
    """Write parasitics bench Markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    figure_block = f"\n![Parasitics summary]({svg_name})\n" if svg_name else ""
    body = f"""# Parasitics report — {switch_type}

| Metric | Value |
| --- | --- |
| Charge injection Q | {q_inj_coulomb:.3e} C |
| Injection step V_inj | {v_inj_v:.3e} V |
| Dummy reduction | {dummy_reduction_pct:.1f} % |
| Clock feedthrough V_cf | {v_feedthrough_v:.3e} V |
| Feedthrough attenuation | {attenuation_db:.1f} dB |
{figure_block}"""
    path.write_text(body, encoding="utf-8")


def refresh_reports_after_bench(output_dir: Path, *, switch_type: str) -> list[Path]:
    """Regenerate per-switch and engine-level ``REPORT.md`` after a bench run."""
    written: list[Path] = []
    switch_report = write_switch_type_report(output_dir, switch_type=switch_type)
    if switch_report is not None:
        written.append(switch_report)
    engine_root = output_dir.parent
    if (engine_root / "compare" / "switch_comparison.json").is_file():
        summary = write_summary_report(engine_root)
        if summary is not None:
            written.append(summary)
    return written


def write_switch_type_report(output_dir: Path, *, switch_type: str) -> Path | None:
    """Write per-switch ``REPORT.md`` linking bench reports and figures."""
    ron_report = output_dir / "RON_REPORT.md"
    noise_report = output_dir / "NOISE_REPORT.md"
    parasitics_report = output_dir / "PARASITICS_REPORT.md"
    if not any(p.is_file() for p in (ron_report, noise_report, parasitics_report)):
        return None

    label = PAPER_LABELS.get(switch_type, switch_type)
    lines = [
        f"# {switch_type} ({label})",
        "",
        f"- **Generated:** {_utc_timestamp()}",
        "",
        "## Bench reports",
        "",
    ]
    if ron_report.is_file():
        lines.append("- [Ron sweep](RON_REPORT.md)")
    if noise_report.is_file():
        lines.append("- [Noise spectrum](NOISE_REPORT.md)")
    if parasitics_report.is_file():
        lines.append("- [Parasitics](PARASITICS_REPORT.md)")
    lines.extend(["", "## Figures", ""])
    for name, caption in (
        ("ron_sweep.svg", "Ron vs Vin"),
        ("noise_spectrum.svg", "Channel noise spectrum"),
        ("parasitics_summary.svg", "Parasitics summary"),
    ):
        fig = output_dir / name
        if fig.is_file():
            lines.append(_figure_block(name, caption))

    metrics_path = output_dir / "switch_metrics.json"
    if metrics_path.is_file():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        lines.extend(["## Metrics", "", "| Metric | Value |", "| --- | --- |"])
        if "ron" in metrics:
            ron = metrics["ron"]
            lines.append(f"| Ron min | {_fmt_float(ron.get('ron_min_ohm'), unit='Ω')} |")
            lines.append(f"| Ron max | {_fmt_float(ron.get('ron_max_ohm'), unit='Ω')} |")
            lines.append(
                f"| Linearity error | {_fmt_float(ron.get('linearity_error_pct'), unit='%')} |"
            )
        if "noise" in metrics:
            noise = metrics["noise"]
            lines.append(
                f"| Flicker corner | {_fmt_float(noise.get('flicker_corner_hz'), unit='Hz')} |"
            )
        if "charge_injection" in metrics:
            chg = metrics["charge_injection"]
            lines.append(f"| V_inj | {_fmt_float(chg.get('v_inj_v'), unit='V')} |")
        if "clock_feedthrough" in metrics:
            cf = metrics["clock_feedthrough"]
            lines.append(f"| V_cf | {_fmt_float(cf.get('v_feedthrough_v'), unit='V')} |")
        lines.append("")

    path = output_dir / "REPORT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_summary_report(output_root: Path) -> Path | None:
    """Write top-level ``REPORT.md`` with comparison table and figure gallery."""
    comparison_path = output_root / "compare" / "switch_comparison.json"
    if not comparison_path.is_file():
        return None

    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    lines = [
        "# switch-model — simulation summary",
        "",
        f"- **Generated:** {_utc_timestamp()}",
        f"- **Output root:** `{output_root.name}/`",
        "",
        "Reference: Zhou et al., *Flicker Noise Analysis on Chopper Amplifier*, "
        "IEEE NEWCAS 2021.",
        "",
        "## Switch comparison",
        "",
        "| Type | Label | Ron@Vcm (Ω) | Linearity err (%) | Flicker corner (Hz) "
        "| V_inj (mV) | V_cf (mV) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for stype in SWITCH_TYPES:
        if stype not in comparison:
            continue
        m = comparison[stype]
        ron = m.get("ron", {})
        noise = m.get("noise", {})
        chg = m.get("charge_injection", {})
        cf = m.get("clock_feedthrough", {})
        v_inj_mv = chg.get("v_inj_v", 0.0) * 1.0e3
        v_cf_mv = cf.get("v_feedthrough_v", 0.0) * 1.0e3
        lines.append(
            f"| `{stype}` | {PAPER_LABELS.get(stype, stype)} "
            f"| {_fmt_float(ron.get('ron_at_vcm_ohm'))} "
            f"| {_fmt_float(ron.get('linearity_error_pct'))} "
            f"| {_fmt_float(noise.get('flicker_corner_hz'))} "
            f"| {_fmt_float(v_inj_mv)} "
            f"| {_fmt_float(v_cf_mv)} |"
        )

    lines.extend(["", "## Per-switch reports", ""])
    for stype in SWITCH_TYPES:
        sub = output_root / stype
        if (sub / "REPORT.md").is_file():
            lines.append(f"- [{stype} ({PAPER_LABELS.get(stype, stype)})]({stype}/REPORT.md)")

    lines.extend(["", "## Figure gallery", ""])
    for stype in SWITCH_TYPES:
        sub = output_root / stype
        for name, caption_suffix in (
            ("ron_sweep.svg", "Ron vs Vin"),
            ("noise_spectrum.svg", "noise"),
            ("parasitics_summary.svg", "parasitics"),
        ):
            fig = sub / name
            if fig.is_file():
                lines.append(_figure_block(f"{stype}/{name}", f"{stype} — {caption_suffix}"))

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "| Path | Description |",
            "| --- | --- |",
            "| `compare/switch_comparison.json` | Cross-type metrics |",
            "| `<type>/ron_sweep.csv` | Ron sweep data |",
            "| `<type>/noise_spectrum.csv` | Noise spectrum data |",
            "| `<type>/switch_metrics.json` | Per-type metrics |",
            "",
        ]
    )

    path = output_root / "REPORT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_engine_comparison_report(
    output_root: Path,
    result: object,
    *,
    engines: tuple[str, ...],
) -> Path:
    """Write top-level cross-engine ``REPORT.md`` under ``output_root``."""
    from switch_model.compare import CompareResult

    if not isinstance(result, CompareResult):
        msg = "result must be CompareResult"
        raise TypeError(msg)

    compared = ", ".join(result.engines_compared)
    lines = [
        "# switch-model — multi-engine comparison",
        "",
        f"- **Generated:** {_utc_timestamp()}",
        f"- **Engines compared:** {compared}",
        "",
    ]
    if result.spectre_fallback:
        lines.append(
            "- **Spectre status:** excluded from comparison "
            "(all runs fell back to Python — source Cadence env and see "
            "`spectre/*/logs/spectre_ron_sweep.log`)"
        )
        lines.append("")
    lines.extend(
        [
            "Peer engines implement the same Ron equations (see `docs/MODEL.md`):",
            "",
            "| Engine | Implementation |",
            "| --- | --- |",
            "| `python` | Python macromodel |",
            "| `ngspice` | Behavioral SPICE (B-source, same equations) |",
            "| `spectre` | Verilog-A `configurable_switch.va` |",
            "",
            "## Per-engine summaries",
            "",
        ]
    )
    for engine in engines:
        engine_report = output_root / engine / "REPORT.md"
        if engine_report.is_file():
            lines.append(f"- [{engine}]({engine}/REPORT.md)")

    lines.extend(
        [
            "",
            "## Metric spread",
            "",
            "| Switch | Metric | Spread % | Tol % | OK |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in result.rows:
        lines.append(
            f"| `{row['switch_type']}` | `{row['metric']}` | "
            f"{row['spread_pct']:.2f} | {row['tolerance_pct']:.1f} | "
            f"{'yes' if row['passed'] else '**NO**'} |"
        )
    lines.extend(
        [
            "",
            f"**Overall:** {'PASS' if result.passed else 'FAIL'}",
            "",
            "## Figure gallery",
            "",
        ]
    )
    for stype in SWITCH_TYPES:
        for engine in engines:
            sub = output_root / engine / stype
            for name, caption_suffix in (
                ("ron_sweep.svg", "Ron vs Vin"),
                ("noise_spectrum.svg", "noise spectrum"),
                ("parasitics_summary.svg", "parasitics"),
            ):
                fig = sub / name
                if fig.is_file():
                    rel = f"{engine}/{stype}/{name}"
                    lines.append(_figure_block(rel, f"{engine}/{stype} — {caption_suffix}"))

    lines.extend(
        [
            "",
            "Regenerate: `python scripts/compare_engines.py --output-root outputs`",
            "",
        ]
    )
    path = output_root / "REPORT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
