"""ngspice Ron testbench generation and execution.

ngspice uses behavioral SPICE (B-source) implementing the same Ron equations as
the Python macromodel and Spectre Verilog-A. Native Verilog-A is not required.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from switch_model.config import SwitchConfig
from switch_model.io import (
    align_ron_to_vin_grid,
    linear_voltage_sweep,
    log_frequency_sweep,
    package_root,
    read_ngspice_dc_wrdata,
    read_ngspice_noise_wrdata,
    read_ngspice_parasitics_wrdata,
)
from switch_model.model import NoiseSimulationResult, ParasiticSimulationResult, RonSimulationResult
from switch_model.model import simulate_noise as simulate_noise_python
from switch_model.model import simulate_parasitics as simulate_parasitics_python
from switch_model.netlist import drive_voltages, ngspice_ron_probe_expr
from switch_model.noise import channel_current_a, flicker_corner_from_spectrum, flicker_power_at_1hz
from switch_model.parasitics import ChargeInjectionMetrics, ClockFeedthroughMetrics, charge_injection, clock_feedthrough
from switch_model.ron import extract_ron_metrics, switch_ron


class NgspiceNotFoundError(RuntimeError):
    """Raised when the ``ngspice`` executable is not on PATH."""


_K_BOLTZMANN = 1.380649e-23


@dataclass(frozen=True)
class NgspiceNoiseResult:
    """Artifacts from an ngspice noise sweep."""

    netlist_path: Path
    wrdata_path: Path
    log_path: Path


@dataclass(frozen=True)
class NgspiceParasiticsResult:
    """Artifacts from an ngspice parasitics bench."""

    netlist_path: Path
    wrdata_path: Path
    log_path: Path


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


def _format_dc_step(value: float) -> str:
    """Full-precision DC step so ngspice Vin aligns with ``numpy.linspace``.

    ``.12g`` truncates the step so ``(points-1) * step`` overshoots ``vin_stop``,
    which drops the final sweep point and leaves the last Ron value stale.
    """
    return repr(value)


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
        "vin_step_v": _format_dc_step(
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
    """Run Ron sweep in ngspice and return metrics on the Python Vin grid."""
    artifacts = run_ngspice_ron(cfg, output_dir)
    dc = read_ngspice_dc_wrdata(artifacts.wrdata_path)
    vin_ref = linear_voltage_sweep(
        cfg.sweep.vin_start_v,
        cfg.sweep.vin_stop_v,
        cfg.sweep.vin_points,
    )
    ron_ref = align_ron_to_vin_grid(vin_ref, dc["vin_v"], dc["ron_ohm"])
    # ngspice may still omit vin_stop when step rounding overshoots; pin endpoint Ron.
    if not np.isclose(dc["vin_v"][-1], vin_ref[-1], rtol=0.0, atol=1.0e-9):
        vclk, _ = drive_voltages(cfg)
        ron_ref[-1] = switch_ron(float(vin_ref[-1]), vclk, cfg)
    metrics = extract_ron_metrics(vin_ref, ron_ref, cfg)
    return RonSimulationResult(vin_v=vin_ref, ron_ohm=ron_ref, metrics=metrics)


def _vcm_v(cfg: SwitchConfig) -> float:
    """Return common-mode bias for noise bench."""
    return 0.5 * (cfg.vdd_v + cfg.vss_v)


def _ron_at_vcm(cfg: SwitchConfig) -> float:
    """Return channel Ron at VCM with switch driven on."""
    vcm = _vcm_v(cfg)
    vclk, _ = drive_voltages(cfg)
    return switch_ron(vcm, vclk, cfg)


def _thermal_resistance_ohm(cfg: SwitchConfig) -> float:
    """Return resistor value for ngspice thermal noise at VCM."""
    noise = cfg.noise
    if not noise.enable_noise:
        return 1.0e12
    if noise.en_white_v_per_sqrt_hz > 0.0:
        kT = _K_BOLTZMANN * noise.temperature_k
        return (noise.en_white_v_per_sqrt_hz**2) / (4.0 * kT)
    return _ron_at_vcm(cfg)


def _ngspice_flicker_control_expr(cfg: SwitchConfig) -> str:
    """Return ngspice ``.control`` expression for flicker voltage density (V/√Hz)."""
    noise = cfg.noise
    if not noise.enable_noise:
        return "0"
    vcm = _vcm_v(cfg)
    vclk, _ = drive_voltages(cfg)
    ron = _ron_at_vcm(cfg)
    current = channel_current_a(vcm, vcm, ron)
    if noise.kf > 0.0 and abs(current) > 0.0:
        pwr_1hz = flicker_power_at_1hz(noise, current)
        return f"sqrt({_format_value(pwr_1hz)} / (frequency ^ {_format_value(noise.en_flicker_ef)}))"
    en_1hz = noise.en_flicker_1hz_v_per_sqrt_hz
    ef_half = 0.5 * noise.en_flicker_ef
    return f"({_format_value(en_1hz)}) / (frequency ^ ({_format_value(ef_half)}))"


def render_ngspice_noise_netlist(template_path: Path, cfg: SwitchConfig) -> str:
    """Render ngspice channel noise netlist (``.noise`` at VCM bias)."""
    text = template_path.read_text(encoding="utf-8")
    vclk, vclk_bar = drive_voltages(cfg)
    replacements = {
        "vclk_v": _format_value(vclk),
        "vclk_bar_v": _format_value(vclk_bar),
        "vin_vcm_v": _format_value(_vcm_v(cfg)),
        "ron_ohm": _format_value(_thermal_resistance_ohm(cfg)),
    }
    for key, val in replacements.items():
        text = text.replace(f"PLACEHOLDER_{key.upper()}", val)
        text = re.sub(
            rf"^\.param\s+{key}=.*$",
            f".param {key}={val}",
            text,
            flags=re.MULTILINE,
        )
    text = (
        text.replace("PLACEHOLDER_DEC", str(cfg.sweep.points_per_decade))
        .replace("PLACEHOLDER_FSTART", _format_value(cfg.sweep.f_start_hz))
        .replace("PLACEHOLDER_FSTOP", _format_value(cfg.sweep.f_stop_hz))
        .replace("PLACEHOLDER_FLICKER_EXPR", _ngspice_flicker_control_expr(cfg))
    )
    return text


def run_ngspice_noise(cfg: SwitchConfig, output_dir: Path) -> NgspiceNoiseResult:
    """Run ngspice ``.noise`` and write ``noise_spectrum.raw``."""
    repo = package_root()
    template = repo / "testbench" / "ngspice" / "noise_sweep.cir"
    ng_dir = output_dir / "ngspice"
    logs_dir = output_dir / "logs"
    ng_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    netlist_path = ng_dir / "noise_sweep.cir"
    netlist_path.write_text(render_ngspice_noise_netlist(template, cfg), encoding="utf-8")
    log_path = logs_dir / "ngspice_noise.log"
    wrdata_path = ng_dir / "noise_spectrum.raw"

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
        msg = f"ngspice noise failed with code {completed.returncode}; see {log_path}"
        raise RuntimeError(msg)
    if not wrdata_path.is_file():
        msg = f"ngspice did not produce {wrdata_path}"
        raise RuntimeError(msg)
    return NgspiceNoiseResult(
        netlist_path=netlist_path,
        wrdata_path=wrdata_path,
        log_path=log_path,
    )


def simulate_noise_ngspice(cfg: SwitchConfig, output_dir: Path) -> NoiseSimulationResult:
    """Run ngspice noise bench; thermal + flicker merged in netlist ``.control``."""
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    status_path = logs_dir / "ngspice_engine_status.json"
    fallback_log = logs_dir / "ngspice_noise_fallback.log"
    try:
        artifacts = run_ngspice_noise(cfg, output_dir)
        parsed = read_ngspice_noise_wrdata(artifacts.wrdata_path)
        frequency_hz = parsed["frequency_hz"]
        spectrum = parsed["noise_v_per_sqrt_hz"]
        vcm = _vcm_v(cfg)
        result = NoiseSimulationResult(
            frequency_hz=frequency_hz,
            noise_v_per_sqrt_hz=spectrum,
            flicker_corner_hz=flicker_corner_from_spectrum(frequency_hz, spectrum, cfg=cfg),
        )
        status_path.write_text(
            json.dumps({"noise_source": "ngspice_behavioral"}),
            encoding="utf-8",
        )
        if fallback_log.is_file():
            fallback_log.unlink()
        return result
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        fallback_log.write_text(f"ngspice noise fallback to Python: {exc}\n", encoding="utf-8")
        status_path.write_text(
            json.dumps({"noise_source": "python_fallback", "reason": str(exc)}),
            encoding="utf-8",
        )
        return simulate_noise_python(cfg)


def render_ngspice_parasitics_netlist(template_path: Path, cfg: SwitchConfig) -> str:
    """Render ngspice parasitics bench with macromodel metric literals."""
    charge = charge_injection(cfg)
    feed = clock_feedthrough(cfg)
    replacements = {
        "q_inj_c": _format_value(charge.q_inj_coulomb),
        "v_inj_v": _format_value(charge.v_inj_v),
        "v_cf_v": _format_value(feed.v_feedthrough_v),
        "atten_db": _format_value(feed.attenuation_db),
        "dummy_reduction_pct": _format_value(charge.dummy_reduction_pct),
    }
    text = template_path.read_text(encoding="utf-8")
    for key, val in replacements.items():
        text = text.replace(f"PLACEHOLDER_{key.upper()}", val)
    return text


def run_ngspice_parasitics(cfg: SwitchConfig, output_dir: Path) -> NgspiceParasiticsResult:
    """Run ngspice parasitics bench and write ``parasitics.raw``."""
    repo = package_root()
    template = repo / "testbench" / "ngspice" / "parasitics_bench.cir"
    ng_dir = output_dir / "ngspice"
    logs_dir = output_dir / "logs"
    ng_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    netlist_path = ng_dir / "parasitics_bench.cir"
    netlist_path.write_text(render_ngspice_parasitics_netlist(template, cfg), encoding="utf-8")
    log_path = logs_dir / "ngspice_parasitics.log"
    wrdata_path = ng_dir / "parasitics.raw"

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
        msg = f"ngspice parasitics failed with code {completed.returncode}; see {log_path}"
        raise RuntimeError(msg)
    if not wrdata_path.is_file():
        msg = f"ngspice did not produce {wrdata_path}"
        raise RuntimeError(msg)
    return NgspiceParasiticsResult(
        netlist_path=netlist_path,
        wrdata_path=wrdata_path,
        log_path=log_path,
    )


def simulate_parasitics_ngspice(cfg: SwitchConfig, output_dir: Path) -> ParasiticSimulationResult:
    """Run parasitics via ngspice control bench; fall back to Python on failure."""
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    status_path = logs_dir / "ngspice_parasitics_status.json"
    fallback_log = logs_dir / "ngspice_parasitics_fallback.log"
    try:
        artifacts = run_ngspice_parasitics(cfg, output_dir)
        parsed = read_ngspice_parasitics_wrdata(artifacts.wrdata_path)
        ref_charge = charge_injection(cfg)
        ref_feed = clock_feedthrough(cfg)
        charge = ChargeInjectionMetrics(
            q_inj_coulomb=parsed["q_inj_coulomb"],
            v_inj_v=parsed["v_inj_v"],
            cgs_contribution_c=ref_charge.cgs_contribution_c,
            cgd_contribution_c=ref_charge.cgd_contribution_c,
            dummy_reduction_pct=parsed["dummy_reduction_pct"],
        )
        feed = ClockFeedthroughMetrics(
            v_feedthrough_v=parsed["v_feedthrough_v"],
            cgd_f=ref_feed.cgd_f,
            c_load_f=ref_feed.c_load_f,
            attenuation_db=parsed["attenuation_db"],
        )
        status_path.write_text(
            json.dumps({"parasitics_source": "ngspice_behavioral"}),
            encoding="utf-8",
        )
        if fallback_log.is_file():
            fallback_log.unlink()
        return ParasiticSimulationResult(charge=charge, feedthrough=feed)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        fallback_log.write_text(f"ngspice parasitics fallback to Python: {exc}\n", encoding="utf-8")
        status_path.write_text(
            json.dumps({"parasitics_source": "python_fallback", "reason": str(exc)}),
            encoding="utf-8",
        )
        return simulate_parasitics_python(cfg)


def archive_veriloga_copy(output_dir: Path) -> Path:
    """Copy Verilog-A sources into output logs for traceability."""
    repo = package_root()
    dest = output_dir / "logs" / "veriloga"
    dest.mkdir(parents=True, exist_ok=True)
    for va in (repo / "veriloga").glob("*.va"):
        target = dest / va.name
        target.write_text(va.read_text(encoding="utf-8"), encoding="utf-8")
    return dest
