"""Cadence Spectre Ron / noise testbench runner (Verilog-A)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from switch_model.config import SwitchConfig
from switch_model.io import log_frequency_sweep, package_root
from switch_model.model import NoiseSimulationResult, ParasiticSimulationResult, RonSimulationResult
from switch_model.model import simulate_noise as simulate_noise_python
from switch_model.model import simulate_parasitics as simulate_parasitics_python
from switch_model.model import simulate_ron_sweep as simulate_ron_python
from switch_model.netlist import drive_voltages, switch_kind_id
from switch_model.noise import flicker_corner_from_spectrum
from switch_model.parasitics import ChargeInjectionMetrics, ClockFeedthroughMetrics, charge_injection, clock_feedthrough
from switch_model.spectre_psf import (
    SpectrePsfError,
    read_spectre_dc_ron,
    read_spectre_noise_from_netlists,
    read_spectre_parasitics_psf,
)


class SpectreNotFoundError(RuntimeError):
    """Raised when the ``spectre`` executable is not on PATH."""


def find_spectre_executable() -> str:
    """Return the Spectre binary path or raise ``SpectreNotFoundError``."""
    found = shutil.which("spectre")
    if found:
        return found
    raise SpectreNotFoundError(
        "Cadence Spectre not found on PATH. Source your Cadence environment "
        "before running Spectre, or use --simulator python."
    )


def _format_param(value: float | int) -> str:
    """Format a template parameter for Spectre netlists."""
    if isinstance(value, int):
        return str(value)
    return f"{value:.12g}"


def _absolutize_va_includes(text: str, repo_root: Path) -> str:
    """Replace relative ahdl_include paths with absolute Verilog-A paths."""
    va_switch = (repo_root / "veriloga" / "configurable_switch.va").resolve()
    return text.replace(
        'ahdl_include "../../veriloga/configurable_switch.va"',
        f'ahdl_include "{va_switch}"',
    )


def render_spectre_ron_netlist(template_path: Path, cfg: SwitchConfig) -> str:
    """Render Spectre Ron DC netlist with VA parameters."""
    repo = package_root()
    text = template_path.read_text(encoding="utf-8")
    vclk, vclk_bar = drive_voltages(cfg)
    noise = cfg.noise
    overrides = {
        "switch_kind": switch_kind_id(cfg),
        "vth_n_v": cfg.vth_n_v,
        "vth_p_v": cfg.vth_p_v,
        "k_n": cfg.k_n,
        "k_p": cfg.k_p,
        "ratio": cfg.ratio,
        "ron_bs_ohm": cfg.ron_bs_ohm,
        "roff_ohm": cfg.roff_ohm,
        "vdd_v": cfg.vdd_v,
        "vclk_v": vclk,
        "vclk_bar_v": vclk_bar,
        "vin_start_v": cfg.sweep.vin_start_v,
        "vin_stop_v": cfg.sweep.vin_stop_v,
        "vin_step_v": (cfg.sweep.vin_stop_v - cfg.sweep.vin_start_v)
        / max(cfg.sweep.vin_points - 1, 1),
        "cgs_f": cfg.cgs_f,
        "cgd_f": cfg.cgd_f,
        "cp1_f": cfg.cp1_f,
        "cp2_f": cfg.cp2_f,
        "cgs_dummy_f": cfg.cgs_dummy_f,
        "cgd_dummy_f": cfg.cgd_dummy_f,
        "en_flicker_1hz_v_per_sqrt_hz": noise.en_flicker_1hz_v_per_sqrt_hz,
        "en_flicker_ef": noise.en_flicker_ef,
        "kf": noise.kf,
        "af": noise.af,
        "enable_noise": 0,
    }
    for name, value in overrides.items():
        text = re.sub(
            rf"^parameters\s+{name}=.*$",
            f"parameters {name}={_format_param(value)}",
            text,
            flags=re.MULTILINE,
        )
    return _absolutize_va_includes(text, repo)


@dataclass(frozen=True)
class SpectreNoiseResult:
    """Artifacts from a Spectre noise analysis run."""

    netlist_path: Path
    log_path: Path
    psf_dir: Path


@dataclass(frozen=True)
class SpectreParasiticsResult:
    """Artifacts from a Spectre parasitics bench run."""

    netlist_path: Path
    log_path: Path
    psf_dir: Path


@dataclass(frozen=True)
class SpectreRunResult:
    """Artifacts from a Spectre run."""

    netlist_path: Path
    log_path: Path
    psf_dir: Path


def _spectre_env() -> dict[str, str]:
    """Return subprocess environment for Spectre (inherits caller env, no license injection)."""
    return os.environ.copy()


def run_spectre_netlist(
    netlist: Path,
    *,
    cwd: Path,
    log_name: str = "spectre.log",
) -> subprocess.CompletedProcess[str]:
    """Execute Spectre on a rendered netlist."""
    executable = find_spectre_executable()
    return subprocess.run(
        [executable, str(netlist.resolve()), "+log", log_name],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=_spectre_env(),
    )


def run_spectre_ron(cfg: SwitchConfig, output_dir: Path) -> SpectreRunResult:
    """Run Spectre DC Ron sweep with Verilog-A switch."""
    repo = package_root()
    template = repo / "testbench" / "spectre" / "ron_sweep.scs"
    logs_dir = output_dir / "logs" / "netlists"
    logs_dir.mkdir(parents=True, exist_ok=True)

    netlist_path = logs_dir / "ron_sweep.scs"
    netlist_path.write_text(render_spectre_ron_netlist(template, cfg), encoding="utf-8")
    log_path = output_dir / "logs" / "spectre_ron_sweep.log"
    completed = run_spectre_netlist(netlist_path, cwd=logs_dir, log_name="spectre_ron.log")
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        msg = f"Spectre failed with code {completed.returncode}; see {log_path}"
        raise RuntimeError(msg)
    psf_dir = logs_dir / "ron_sweep.raw"
    return SpectreRunResult(netlist_path=netlist_path, log_path=log_path, psf_dir=psf_dir)


def simulate_ron_spectre(cfg: SwitchConfig, output_dir: Path) -> RonSimulationResult:
    """Run Ron sweep in Spectre (VA) and parse PSF; fall back to Python on PSF error."""
    from switch_model.ngspice_engine import archive_veriloga_copy

    archive_veriloga_copy(output_dir)
    try:
        artifacts = run_spectre_ron(cfg, output_dir)
        result = read_spectre_dc_ron(artifacts.psf_dir, cfg)
        status_path = output_dir / "logs" / "spectre_engine_status.json"
        status_path.write_text(
            json.dumps({"ron_source": "spectre_va", "psf_dir": str(artifacts.psf_dir)}),
            encoding="utf-8",
        )
        fallback_log = output_dir / "logs" / "spectre_ron_fallback.log"
        if fallback_log.is_file():
            fallback_log.unlink()
        return result
    except (SpectrePsfError, RuntimeError, FileNotFoundError) as exc:
        log_path = output_dir / "logs" / "spectre_ron_fallback.log"
        log_path.write_text(f"Spectre Ron fallback to Python: {exc}\n", encoding="utf-8")
        status_path = output_dir / "logs" / "spectre_engine_status.json"
        status_path.write_text(
            '{"ron_source": "python_fallback", "reason": "spectre_run_failed"}\n',
            encoding="utf-8",
        )
        return simulate_ron_python(cfg)


def render_spectre_noise_netlist(template_path: Path, cfg: SwitchConfig) -> str:
    """Render Spectre channel noise netlist with VA parameters."""
    repo = package_root()
    text = template_path.read_text(encoding="utf-8")
    vclk, vclk_bar = drive_voltages(cfg)
    vcm = 0.5 * (cfg.vdd_v + cfg.vss_v)
    noise = cfg.noise
    overrides = {
        "switch_kind": switch_kind_id(cfg),
        "vth_n_v": cfg.vth_n_v,
        "vth_p_v": cfg.vth_p_v,
        "k_n": cfg.k_n,
        "k_p": cfg.k_p,
        "ratio": cfg.ratio,
        "ron_bs_ohm": cfg.ron_bs_ohm,
        "roff_ohm": cfg.roff_ohm,
        "vdd_v": cfg.vdd_v,
        "vclk_v": vclk,
        "vclk_bar_v": vclk_bar,
        "vin_vcm_v": vcm,
        "cgs_f": cfg.cgs_f,
        "cgd_f": cfg.cgd_f,
        "cp1_f": cfg.cp1_f,
        "cp2_f": cfg.cp2_f,
        "cgs_dummy_f": cfg.cgs_dummy_f,
        "cgd_dummy_f": cfg.cgd_dummy_f,
        "en_flicker_1hz_v_per_sqrt_hz": noise.en_flicker_1hz_v_per_sqrt_hz,
        "en_flicker_ef": noise.en_flicker_ef,
        "kf": noise.kf,
        "af": noise.af,
        "enable_noise": 1 if noise.enable_noise else 0,
        "f_start": cfg.sweep.f_start_hz,
        "f_stop": cfg.sweep.f_stop_hz,
        "dec": cfg.sweep.points_per_decade,
    }
    for name, value in overrides.items():
        text = re.sub(
            rf"^parameters\s+{name}=.*$",
            f"parameters {name}={_format_param(value)}",
            text,
            flags=re.MULTILINE,
        )
    return _absolutize_va_includes(text, repo)


def run_spectre_noise(cfg: SwitchConfig, output_dir: Path) -> SpectreNoiseResult:
    """Run Spectre noise analysis with Verilog-A switch."""
    repo = package_root()
    template = repo / "testbench" / "spectre" / "noise_sweep.scs"
    logs_dir = output_dir / "logs" / "netlists"
    logs_dir.mkdir(parents=True, exist_ok=True)

    netlist_path = logs_dir / "noise_sweep.scs"
    netlist_path.write_text(render_spectre_noise_netlist(template, cfg), encoding="utf-8")
    log_path = output_dir / "logs" / "spectre_noise_sweep.log"
    completed = run_spectre_netlist(netlist_path, cwd=logs_dir, log_name="spectre_noise.log")
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        msg = f"Spectre noise failed with code {completed.returncode}; see {log_path}"
        raise RuntimeError(msg)
    psf_dir = logs_dir / "noise_sweep.raw"
    return SpectreNoiseResult(netlist_path=netlist_path, log_path=log_path, psf_dir=psf_dir)


def simulate_noise_spectre(cfg: SwitchConfig, output_dir: Path) -> NoiseSimulationResult:
    """Run Spectre VA noise bench and parse PSF; fall back to Python on failure."""
    from switch_model.ngspice_engine import archive_veriloga_copy

    archive_veriloga_copy(output_dir)
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    status_path = logs_dir / "spectre_engine_status.json"
    fallback_log = logs_dir / "spectre_noise_fallback.log"
    vcm = 0.5 * (cfg.vdd_v + cfg.vss_v)
    try:
        artifacts = run_spectre_noise(cfg, output_dir)
        parsed = read_spectre_noise_from_netlists(
            artifacts.netlist_path.parent,
            stem=artifacts.netlist_path.stem,
            signal="N1",
            cfg=cfg,
        )
        frequency_hz = log_frequency_sweep(
            cfg.sweep.f_start_hz,
            cfg.sweep.f_stop_hz,
            cfg.sweep.points_per_decade,
        )
        log_f = np.log10(frequency_hz)
        log_sim = np.log10(np.maximum(parsed["frequency_hz"], 1.0e-30))
        spectrum = np.interp(
            log_f,
            log_sim,
            parsed["noise_v_per_sqrt_hz"],
        ).astype(np.float64)
        result = NoiseSimulationResult(
            frequency_hz=frequency_hz,
            noise_v_per_sqrt_hz=spectrum,
            flicker_corner_hz=flicker_corner_from_spectrum(frequency_hz, spectrum, cfg=cfg),
        )
        status_path.write_text(
            json.dumps({"noise_source": "spectre_va", "psf_dir": str(artifacts.psf_dir)}),
            encoding="utf-8",
        )
        if fallback_log.is_file():
            fallback_log.unlink()
        return result
    except (SpectrePsfError, RuntimeError, FileNotFoundError) as exc:
        fallback_log.write_text(f"Spectre noise fallback to Python: {exc}\n", encoding="utf-8")
        status_path.write_text(
            json.dumps({"noise_source": "python_fallback", "reason": str(exc)}),
            encoding="utf-8",
        )
        return simulate_noise_python(cfg)


def render_spectre_parasitics_netlist(template_path: Path, cfg: SwitchConfig) -> str:
    """Render Spectre parasitics bench with macromodel metric literals."""
    charge = charge_injection(cfg)
    feed = clock_feedthrough(cfg)
    replacements = {
        "q_inj_c": _format_param(charge.q_inj_coulomb),
        "v_inj_v": _format_param(charge.v_inj_v),
        "v_cf_v": _format_param(feed.v_feedthrough_v),
        "atten_db": _format_param(feed.attenuation_db),
        "dummy_reduction_pct": _format_param(charge.dummy_reduction_pct),
    }
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"PLACEHOLDER_{key.upper()}", value)
    return text


def run_spectre_parasitics(cfg: SwitchConfig, output_dir: Path) -> SpectreParasiticsResult:
    """Run Spectre parasitics DC bench and write PSF scalars."""
    repo = package_root()
    template = repo / "testbench" / "spectre" / "parasitics_bench.scs"
    logs_dir = output_dir / "logs" / "netlists"
    logs_dir.mkdir(parents=True, exist_ok=True)

    netlist_path = logs_dir / "parasitics_bench.scs"
    netlist_path.write_text(render_spectre_parasitics_netlist(template, cfg), encoding="utf-8")
    log_path = output_dir / "logs" / "spectre_parasitics.log"
    completed = run_spectre_netlist(netlist_path, cwd=logs_dir, log_name="spectre_parasitics.log")
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        msg = f"Spectre parasitics failed with code {completed.returncode}; see {log_path}"
        raise RuntimeError(msg)
    psf_dir = logs_dir / "parasitics_bench.raw"
    return SpectreParasiticsResult(netlist_path=netlist_path, log_path=log_path, psf_dir=psf_dir)


def simulate_parasitics_spectre(cfg: SwitchConfig, output_dir: Path) -> ParasiticSimulationResult:
    """Run parasitics via Spectre DC bench; fall back to Python on failure."""
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    status_path = logs_dir / "spectre_parasitics_status.json"
    fallback_log = logs_dir / "spectre_parasitics_fallback.log"
    try:
        artifacts = run_spectre_parasitics(cfg, output_dir)
        parsed = read_spectre_parasitics_psf(artifacts.psf_dir)
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
            json.dumps({"parasitics_source": "spectre_behavioral", "psf_dir": str(artifacts.psf_dir)}),
            encoding="utf-8",
        )
        if fallback_log.is_file():
            fallback_log.unlink()
        return ParasiticSimulationResult(charge=charge, feedthrough=feed)
    except (SpectrePsfError, RuntimeError, FileNotFoundError) as exc:
        fallback_log.write_text(f"Spectre parasitics fallback to Python: {exc}\n", encoding="utf-8")
        status_path.write_text(
            json.dumps({"parasitics_source": "python_fallback", "reason": str(exc)}),
            encoding="utf-8",
        )
        return simulate_parasitics_python(cfg)
