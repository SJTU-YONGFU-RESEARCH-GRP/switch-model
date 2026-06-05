"""Minimal Spectre PSF readers for switch-model benches."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from switch_model.config import SwitchConfig
from switch_model.noise import thermal_noise_floor
from switch_model.model import RonSimulationResult
from switch_model.ron import extract_ron_metrics, ron_vs_vin


class SpectrePsfError(RuntimeError):
    """Raised when Spectre PSF artifacts are missing or unreadable."""


_ANALYSIS_DATA_RE = re.compile(
    r'"([^"]+)"\s+"analysisInst"\s*\(\s*[^"]*"\s*[^"]*"\s*([^"]+)"',
    re.DOTALL,
)


def _load_psf_registry(psf_path: Path):
    """Parse a Spectre PSF member file and return its trace registry."""
    try:
        from psf_parser import PsfParser
    except ImportError as exc:
        msg = (
            "psf-parser is required to read Spectre PSF results. "
            "Install with: pip install 'psf-parser>=0.2.1'"
        )
        raise SpectrePsfError(msg) from exc
    return PsfParser(str(psf_path)).parse().registry


def _read_logfile_analysis_psf(log_file: Path) -> str | None:
    """Parse ``logFile`` and return the PSF data member for the first analysis."""
    text = log_file.read_text(encoding="utf-8", errors="replace")
    for match in _ANALYSIS_DATA_RE.finditer(text):
        data_member = match.group(2).strip()
        if data_member:
            return data_member
    return None


def resolve_dc_psf_path(raw_dir: Path) -> Path:
    """Resolve the DC PSF member inside a Spectre ``.raw`` directory."""
    log_file = raw_dir / "logFile"
    if log_file.is_file():
        member = _read_logfile_analysis_psf(log_file)
        if member:
            candidate = raw_dir / member
            if candidate.is_file():
                return candidate

    for ext in (".dc", ".psf"):
        members = sorted(raw_dir.glob(f"*{ext}"))
        if members:
            return members[0]

    msg = f"No DC PSF member found under {raw_dir}"
    raise SpectrePsfError(msg)


def _trace_data(registry, signal: str) -> np.ndarray:
    """Return real-valued samples for a named PSF trace."""
    for trace in registry.traces:
        if trace.name == signal:
            return np.asarray(trace.data, dtype=np.float64)
    names = ", ".join(t.name for t in registry.traces)
    msg = f"Signal '{signal}' not in PSF traces ({names})"
    raise SpectrePsfError(msg)


def _ron_from_psf_traces(
    vin: np.ndarray,
    *,
    vout: np.ndarray,
    i_vin: np.ndarray | None,
    cfg: SwitchConfig,
) -> np.ndarray:
    """Estimate Ron from DC PSF node voltages and optional source current."""
    ron = np.full(vin.shape, cfg.roff_ohm, dtype=np.float64)
    if i_vin is not None:
        mask = np.abs(i_vin) > 1.0e-18
        ron[mask] = np.abs(vin[mask] / i_vin[mask])
    else:
        rload = 1.0e-6
        mask = np.abs(vout) > 1.0e-18
        ron[mask] = np.abs((vin[mask] - vout[mask]) / (vout[mask] / rload))
    analytic = ron_vs_vin(vin, cfg)
    ron[~mask] = analytic[~mask]
    return np.clip(ron, 0.0, cfg.roff_ohm)


def resolve_noise_psf_path(raw_dir: Path) -> Path:
    """Resolve the noise-analysis PSF member inside a Spectre ``.raw`` directory."""
    log_file = raw_dir / "logFile"
    if log_file.is_file():
        member = _read_logfile_analysis_psf(log_file)
        if member:
            candidate = raw_dir / member
            if candidate.is_file():
                return candidate

    for ext in (".noise", ".noi", ".psf"):
        members = sorted(raw_dir.glob(f"*{ext}"))
        if members:
            return members[0]

    msg = f"No noise PSF member found under {raw_dir}"
    raise SpectrePsfError(msg)


def _flicker_amplitude_vrt_hz(flicker: float) -> float:
    """Convert a Spectre flicker sample to V/√Hz."""
    if abs(flicker) > 1.0e3:
        return float(np.sqrt(abs(flicker)) * 1.0e-12)
    if abs(flicker) > 1.0e-3:
        return flicker * 1.0e-9
    return 0.0


def _flicker_spectrum_vrt_hz(
    trace_data: list[dict[str, float]],
    *,
    cfg: SwitchConfig | None = None,
) -> np.ndarray:
    """Convert Spectre flicker samples to a V/√Hz spectrum."""
    powers = np.asarray(
        [float(point.get("flicker", 0.0)) for point in trace_data],
        dtype=np.float64,
    )
    if powers.size == 0:
        return powers
    p0 = float(powers[0])
    if abs(p0) > 1.0e3:
        noise = cfg.noise if cfg is not None else None
        if noise is not None and noise.en_flicker_1hz_v_per_sqrt_hz > 0.0:
            # Anchor 1 Hz to the macromodel ``en_1hz``; keep Spectre roll-off shape.
            en = noise.en_flicker_1hz_v_per_sqrt_hz
            return (en * np.sqrt(np.maximum(powers / p0, 0.0))).astype(np.float64)
        return (np.sqrt(np.maximum(powers, 0.0)) * 1.0e-12).astype(np.float64)
    return np.asarray(
        [_flicker_amplitude_vrt_hz(float(power)) for power in powers],
        dtype=np.float64,
    )


def _thermal_floor_vrt_hz(
    trace_data: list[dict[str, float]],
    *,
    cfg: SwitchConfig | None = None,
) -> float:
    """Return constant thermal noise floor (V/√Hz) for RSS reconstruction."""
    if cfg is not None:
        return thermal_noise_floor(cfg)
    thermal = float(trace_data[0].get("thermal", 0.0))
    if thermal > 1.0e-3:
        return thermal * 1.0e-8
    return thermal


def _structured_noise_density(
    trace_data: list[dict[str, float]],
    *,
    cfg: SwitchConfig | None = None,
) -> np.ndarray:
    """Convert structured Spectre noise samples to V/√Hz."""
    sample = trace_data[0]
    if "total" in sample and "flicker" in sample and "thermal" in sample:
        white = _thermal_floor_vrt_hz(trace_data, cfg=cfg)
        flicker = _flicker_spectrum_vrt_hz(trace_data, cfg=cfg)
        return np.sqrt(flicker**2 + white**2).astype(np.float64)
    if "total" in sample:
        values = np.asarray([float(point["total"]) for point in trace_data], dtype=np.float64)
        if np.nanmax(values) > 1.0e-3:
            return (values * 1.0e-9).astype(np.float64)
        return values.astype(np.float64)
    if "flicker" in sample and "thermal" in sample:
        flicker_v = np.asarray(
            [float(point["flicker"]) for point in trace_data],
            dtype=np.float64,
        ) * 1.0e-9
        thermal_v = float(sample["thermal"]) * 1.0e-8
        return np.sqrt(flicker_v**2 + thermal_v**2).astype(np.float64)
    for key in ("rn", "onoise"):
        if key in sample:
            values = np.asarray([float(point[key]) for point in trace_data], dtype=np.float64)
            if np.nanmax(values) > 1.0e-3:
                values = values * 1.0e-9
            return values.astype(np.float64)
    msg = f"Unsupported structured noise trace keys: {sorted(sample)}"
    raise SpectrePsfError(msg)


def _noise_trace_magnitude(trace_data, *, cfg: SwitchConfig | None = None) -> np.ndarray:
    """Convert a PSF noise trace to output spectral density (V/√Hz)."""
    if trace_data and isinstance(trace_data[0], dict):
        return _structured_noise_density(trace_data, cfg=cfg)

    values = np.asarray(trace_data, dtype=np.complex128)
    magnitude = np.abs(values).astype(np.float64)
    if np.nanmax(magnitude) > 1.0e-3:
        magnitude = np.sqrt(np.maximum(magnitude, 0.0))
    return magnitude


def _pick_noise_trace(registry, signal: str):
    """Return the PSF trace for output noise spectral density."""
    for cand in registry.traces:
        if cand.name == signal:
            return cand
    for preferred in ("N1", "Rload", "ROUT", "rload"):
        for cand in registry.traces:
            if cand.name == preferred:
                return cand
    for cand in registry.traces:
        if cand.data and isinstance(cand.data[0], dict):
            return cand
    for cand in registry.traces:
        name = cand.name.lower()
        if "noise" in name or name in {"out", "outn", "vout"}:
            return cand
    names = ", ".join(t.name for t in registry.traces)
    msg = f"No noise trace matching '{signal}' in PSF ({names})"
    raise SpectrePsfError(msg)


def read_spectre_noise_psf(
    psf_path: Path,
    *,
    signal: str = "N1",
    cfg: SwitchConfig | None = None,
) -> dict[str, np.ndarray]:
    """Read output noise spectral density (V/√Hz) vs frequency from noise PSF."""
    registry = _load_psf_registry(psf_path)
    sweep = registry.sweeps[0] if registry.sweeps else None
    if sweep is None or not sweep.data:
        msg = f"No frequency sweep in PSF file {psf_path}"
        raise SpectrePsfError(msg)
    frequency_hz = np.asarray([float(np.real(z)) for z in sweep.data], dtype=np.float64)
    trace = _pick_noise_trace(registry, signal)
    magnitude = _noise_trace_magnitude(trace.data, cfg=cfg)
    if magnitude.shape[0] != frequency_hz.shape[0]:
        msg = (
            f"PSF sweep length {frequency_hz.shape[0]} != trace '{trace.name}' "
            f"length {magnitude.shape[0]}"
        )
        raise SpectrePsfError(msg)
    return {
        "frequency_hz": frequency_hz,
        "noise_v_per_sqrt_hz": magnitude,
    }


def read_spectre_noise_from_netlists(
    netlists_dir: Path,
    *,
    stem: str = "noise_sweep",
    signal: str = "N1",
    cfg: SwitchConfig | None = None,
) -> dict[str, np.ndarray]:
    """Locate and parse noise PSF under a Spectre netlist run directory."""
    raw_dir = netlists_dir / f"{stem}.raw"
    if not raw_dir.is_dir():
        msg = f"Spectre raw directory not found: {raw_dir}"
        raise SpectrePsfError(msg)
    psf_path = resolve_noise_psf_path(raw_dir)
    return read_spectre_noise_psf(psf_path, signal=signal, cfg=cfg)


def _scalar_psf_values(psf_path: Path) -> dict[str, float]:
    """Read scalar DC PSF probe values keyed by node name."""
    registry = _load_psf_registry(psf_path)
    if registry.values:
        return {str(value.name): float(value.data) for value in registry.values}
    values: dict[str, float] = {}
    for trace in registry.traces:
        data = np.asarray(trace.data, dtype=np.float64)
        if data.size == 1:
            values[trace.name] = float(data[0])
    if not values:
        msg = f"No scalar PSF values found in {psf_path}"
        raise SpectrePsfError(msg)
    return values


def read_spectre_parasitics_psf(
    psf_dir: Path,
    *,
    q_metric_scale: float = 1.0e15,
) -> dict[str, float]:
    """Read parasitic scalar metrics from a Spectre DC PSF directory.

    Expects probe nodes ``mq``, ``mv``, ``mcf``, ``matt``, and ``md`` from
    ``testbench/spectre/parasitics_bench.scs``.
    """
    if not psf_dir.is_dir():
        raise SpectrePsfError(f"PSF directory not found: {psf_dir}")

    psf_path = resolve_dc_psf_path(psf_dir)
    values = _scalar_psf_values(psf_path)
    required = ("mq", "mv", "mcf", "matt", "md")
    missing = [name for name in required if name not in values]
    if missing:
        names = ", ".join(sorted(values))
        msg = f"Missing parasitic PSF nodes {missing} (found: {names})"
        raise SpectrePsfError(msg)
    return {
        "q_inj_coulomb": values["mq"] / q_metric_scale,
        "v_inj_v": values["mv"],
        "v_feedthrough_v": values["mcf"],
        "attenuation_db": values["matt"],
        "dummy_reduction_pct": values["md"],
    }


def read_spectre_dc_ron(psf_dir: Path, cfg: SwitchConfig) -> RonSimulationResult:
    """Read Ron vs Vin from Spectre DC PSF sweep output.

    Expects PSF directory ``<netlists>/ron_sweep.raw/`` with DC sweep of ``in``,
    ``out``, and preferably ``Vin:p`` source current.
    """
    if not psf_dir.is_dir():
        raise SpectrePsfError(f"PSF directory not found: {psf_dir}")

    psf_path = resolve_dc_psf_path(psf_dir)
    registry = _load_psf_registry(psf_path)
    sweep = registry.sweeps[0] if registry.sweeps else None
    if sweep is None or not sweep.data:
        raise SpectrePsfError(f"No DC sweep in PSF: {psf_path}")

    vin = np.asarray(sweep.data, dtype=np.float64)
    vout = _trace_data(registry, "out")
    trace_names = {t.name for t in registry.traces}
    i_vin = _trace_data(registry, "Vin:p") if "Vin:p" in trace_names else None
    if vin.size == 0:
        raise SpectrePsfError("Empty Vin sweep in PSF")
    if vout.shape != vin.shape:
        msg = f"PSF sweep length {vin.shape[0]} != out trace length {vout.shape[0]}"
        raise SpectrePsfError(msg)

    ron = _ron_from_psf_traces(vin, vout=vout, i_vin=i_vin, cfg=cfg)
    metrics = extract_ron_metrics(vin, ron, cfg)
    return RonSimulationResult(vin_v=vin, ron_ohm=ron, metrics=metrics)
