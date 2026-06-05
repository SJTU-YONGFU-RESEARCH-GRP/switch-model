"""Cadence Spectre Ron / noise testbench runner (Verilog-A)."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from switch_model.config import SwitchConfig
from switch_model.io import package_root
from switch_model.model import NoiseSimulationResult, RonSimulationResult
from switch_model.model import simulate_noise as simulate_noise_python
from switch_model.model import simulate_ron_sweep as simulate_ron_python
from switch_model.netlist import drive_voltages, switch_kind_id
from switch_model.spectre_psf import SpectrePsfError, read_spectre_dc_ron


class SpectreNotFoundError(RuntimeError):
    """Raised when the ``spectre`` executable is not on PATH."""


def find_spectre_executable() -> str:
    """Return the Spectre binary path or raise ``SpectreNotFoundError``."""
    found = shutil.which("spectre")
    if found:
        return found
    for candidate in (
        "/eda/cadence/SPECTRE241/tools/bin/spectre",
        "/eda/cadence/SPECTRE231/tools/bin/spectre",
    ):
        if Path(candidate).is_file():
            return candidate
    raise SpectreNotFoundError(
        "Cadence Spectre not found on PATH. Install Spectre or use --simulator python."
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
        "enable_noise": 1 if noise.enable_noise else 0,
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
class SpectreRunResult:
    """Artifacts from a Spectre run."""

    netlist_path: Path
    log_path: Path
    psf_dir: Path


def run_spectre_netlist(
    netlist: Path,
    *,
    cwd: Path,
    log_name: str = "spectre.log",
) -> subprocess.CompletedProcess[str]:
    """Execute Spectre on a rendered netlist."""
    executable = find_spectre_executable()
    return subprocess.run(
        [executable, str(netlist), "+log", log_name],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
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
        return read_spectre_dc_ron(artifacts.psf_dir, cfg)
    except (SpectrePsfError, RuntimeError, FileNotFoundError) as exc:
        log_path = output_dir / "logs" / "spectre_ron_fallback.log"
        log_path.write_text(f"Spectre Ron fallback to Python: {exc}\n", encoding="utf-8")
        return simulate_ron_python(cfg)


def simulate_noise_spectre(cfg: SwitchConfig, output_dir: Path) -> NoiseSimulationResult:
    """Run noise via Python until Spectre VA noise PSF parser is wired."""
    _ = output_dir
    log_path = output_dir / "logs" / "spectre_noise.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "Spectre noise: using Python macromodel spectrum (VA .noise PSF planned).\n",
        encoding="utf-8",
    )
    return simulate_noise_python(cfg)
