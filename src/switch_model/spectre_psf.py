"""Minimal Spectre PSF readers for switch-model benches."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from switch_model.config import SwitchConfig
from switch_model.model import RonSimulationResult
from switch_model.ron import extract_ron_metrics


class SpectrePsfError(RuntimeError):
    """Raised when Spectre PSF artifacts are missing or unreadable."""


def read_spectre_dc_ron(psf_dir: Path, cfg: SwitchConfig) -> RonSimulationResult:
    """Read Ron vs Vin from Spectre DC PSF sweep output.

    Expects PSF directory ``<netlists>/ron_sweep.raw/`` with DC sweep of ``v(in)``
    and ``v(out)``; Ron is approximated as ``abs(v(in)-v(out))/|I(Rload)|``.
    """
    try:
        from psf_parser import PSF
    except ImportError as exc:
        msg = "psf-parser required for Spectre PSF reads"
        raise SpectrePsfError(msg) from exc

    if not psf_dir.is_dir():
        raise SpectrePsfError(f"PSF directory not found: {psf_dir}")

    psf = PSF(str(psf_dir))
    sweep_name = None
    for candidate in ("dc", "dc.dc", "sweep"):
        if candidate in psf.sweeps:
            sweep_name = candidate
            break
    if sweep_name is None and psf.sweeps:
        sweep_name = next(iter(psf.sweeps))
    if sweep_name is None:
        raise SpectrePsfError(f"No DC sweep in PSF: {psf_dir}")

    sweep = psf.sweeps[sweep_name]
    vin = np.asarray(sweep.get_signal("in"), dtype=np.float64)
    vout = np.asarray(sweep.get_signal("out"), dtype=np.float64)
    if vin.size == 0:
        raise SpectrePsfError("Empty Vin sweep in PSF")

    # Small load resistor in deck: Ron ~ |V(in,out)| / Iload.
    rload = 1.0e-6
    ron = np.abs(vin - vout) / rload
    ron = np.clip(ron, 0.0, cfg.roff_ohm)
    metrics = extract_ron_metrics(vin, ron, cfg)
    return RonSimulationResult(vin_v=vin, ron_ohm=ron, metrics=metrics)
