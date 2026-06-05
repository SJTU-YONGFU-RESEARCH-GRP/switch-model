"""ngspice Ron testbench generation and execution.

ngspice uses behavioral SPICE (B-source) implementing the same Ron equations as
the Python macromodel and Spectre Verilog-A. Native Verilog-A is not required.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from switch_model.config import SwitchConfig
from switch_model.io import package_root, read_ngspice_dc_wrdata
from switch_model.model import NoiseSimulationResult, RonSimulationResult
from switch_model.model import simulate_noise as simulate_noise_python
from switch_model.netlist import drive_voltages, ngspice_ron_probe_expr
from switch_model.ron import extract_ron_metrics


class NgspiceNotFoundError(RuntimeError):
    """Raised when the ``ngspice`` executable is not on PATH."""


@dataclass(frozen=True)
class NgspiceRonResult:
    """Artifacts from an ngspice Ron DC sweep."""

    netlist_path: Path
    wrdata_path: Path
    log_path: Path


def find_ngspice_executable() -> str:
    """Return the ngspice binary path or raise ``NgspiceNotFoundError``."""
    for name in ("ngspice", "ngspice-shared"):
        found = shutil.which(name)
        if found:
            return found
    raise NgspiceNotFoundError(
        "ngspice not found on PATH. Install ngspice or use --simulator python."
    )


def _format_value(value: float) -> str:
    """Format a numeric value for SPICE netlists."""
    return f"{value:.12g}"


def render_ngspice_ron_netlist(template_path: Path, cfg: SwitchConfig) -> str:
    """Render ngspice Ron sweep netlist with macromodel parameters."""
    text = template_path.read_text(encoding="utf-8")
    vclk, vclk_bar = drive_voltages(cfg)
    ron_expr = ngspice_ron_probe_expr(cfg)
    replacements = {
        "vclk_v": _format_value(vclk),
        "vclk_bar_v": _format_value(vclk_bar),
        "vin_start_v": _format_value(cfg.sweep.vin_start_v),
        "vin_stop_v": _format_value(cfg.sweep.vin_stop_v),
        "vin_step_v": _format_value(
            (cfg.sweep.vin_stop_v - cfg.sweep.vin_start_v) / max(cfg.sweep.vin_points - 1, 1)
        ),
        "ron_probe_expr": ron_expr,
    }
    for key, val in replacements.items():
        text = text.replace(f"PLACEHOLDER_{key.upper()}", val)
        text = re.sub(
            rf"^\.param\s+{key}=.*$",
            f".param {key}={val}",
            text,
            flags=re.MULTILINE,
        )
    return text


def run_ngspice_ron(cfg: SwitchConfig, output_dir: Path) -> NgspiceRonResult:
    """Run ngspice DC Ron sweep and write ``ron_sweep.raw``."""
    repo = package_root()
    template = repo / "testbench" / "ngspice" / "ron_sweep.cir"
    ng_dir = output_dir / "ngspice"
    logs_dir = output_dir / "logs"
    ng_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    netlist_path = ng_dir / "ron_sweep.cir"
    netlist_path.write_text(render_ngspice_ron_netlist(template, cfg), encoding="utf-8")
    log_path = logs_dir / "ngspice_ron_sweep.log"
    wrdata_path = ng_dir / "ron_sweep.raw"

    executable = find_ngspice_executable()
    completed = subprocess.run(
        [executable, "-b", netlist_path.name],
        cwd=ng_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        msg = f"ngspice failed with code {completed.returncode}; see {log_path}"
        raise RuntimeError(msg)
    if not wrdata_path.is_file():
        msg = f"ngspice did not produce {wrdata_path}"
        raise RuntimeError(msg)
    return NgspiceRonResult(
        netlist_path=netlist_path,
        wrdata_path=wrdata_path,
        log_path=log_path,
    )


def simulate_ron_ngspice(cfg: SwitchConfig, output_dir: Path) -> RonSimulationResult:
    """Run Ron sweep in ngspice and return aligned metrics."""
    artifacts = run_ngspice_ron(cfg, output_dir)
    dc = read_ngspice_dc_wrdata(artifacts.wrdata_path)
    metrics = extract_ron_metrics(dc["vin_v"], dc["ron_ohm"], cfg)
    return RonSimulationResult(vin_v=dc["vin_v"], ron_ohm=dc["ron_ohm"], metrics=metrics)


def simulate_noise_ngspice(cfg: SwitchConfig, output_dir: Path) -> NoiseSimulationResult:
    """Run noise bench via Python macromodel (ngspice .noise TBD for VA switch)."""
    _ = output_dir
    result = simulate_noise_python(cfg)
    log_path = output_dir / "logs" / "ngspice_noise.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "ngspice noise: using Python macromodel spectrum (VA .noise deck planned).\n",
        encoding="utf-8",
    )
    return result


def archive_veriloga_copy(output_dir: Path) -> Path:
    """Copy Verilog-A sources into output logs for traceability."""
    repo = package_root()
    dest = output_dir / "logs" / "veriloga"
    dest.mkdir(parents=True, exist_ok=True)
    for va in (repo / "veriloga").glob("*.va"):
        target = dest / va.name
        target.write_text(va.read_text(encoding="utf-8"), encoding="utf-8")
    return dest
