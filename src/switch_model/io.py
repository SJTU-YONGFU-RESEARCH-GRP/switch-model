"""Frequency grids, CSV I/O, and repository path helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

RON_COLUMNS = ("vin_v", "ron_ohm")
NOISE_COLUMNS = ("frequency_hz", "noise_v_per_sqrt_hz")


def package_root() -> Path:
    """Return the switch-model repository root (parent of ``src/``)."""
    return Path(__file__).resolve().parents[2]


def log_frequency_sweep(
    f_start_hz: float,
    f_stop_hz: float,
    points_per_decade: int,
) -> NDArray[np.float64]:
    """Return a log-spaced frequency vector (Hz)."""
    if f_start_hz <= 0.0 or f_stop_hz <= f_start_hz:
        msg = f"Invalid sweep: f_start={f_start_hz}, f_stop={f_stop_hz}"
        raise ValueError(msg)
    if points_per_decade < 1:
        raise ValueError("points_per_decade must be >= 1")
    decades = np.log10(f_stop_hz / f_start_hz)
    num_points = max(int(np.ceil(decades * points_per_decade)) + 1, 2)
    return np.logspace(np.log10(f_start_hz), np.log10(f_stop_hz), num_points)


def linear_voltage_sweep(
    v_start_v: float,
    v_stop_v: float,
    num_points: int,
) -> NDArray[np.float64]:
    """Return a linear Vin sweep."""
    if num_points < 2:
        raise ValueError("num_points must be >= 2")
    return np.linspace(v_start_v, v_stop_v, num_points, dtype=np.float64)


def write_ron_csv(path: Path, vin_v: NDArray[np.float64], ron_ohm: NDArray[np.float64]) -> None:
    """Write Ron sweep CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.column_stack([vin_v, ron_ohm])
    np.savetxt(path, data, delimiter=",", header=",".join(RON_COLUMNS), comments="")


def write_noise_csv(
    path: Path,
    frequency_hz: NDArray[np.float64],
    noise_v_per_sqrt_hz: NDArray[np.float64],
) -> None:
    """Write noise spectrum CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.column_stack([frequency_hz, noise_v_per_sqrt_hz])
    np.savetxt(path, data, delimiter=",", header=",".join(NOISE_COLUMNS), comments="")
