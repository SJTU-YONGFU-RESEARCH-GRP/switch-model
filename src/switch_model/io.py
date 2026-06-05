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


def align_ron_to_vin_grid(
    vin_ref: NDArray[np.float64],
    vin_sim: NDArray[np.float64],
    ron_sim: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Map simulated Ron onto the reference Vin grid.

    When ngspice ``wrdata`` Vin values are index-aligned with ``vin_ref`` (same
    length and within microvolt tolerance, as from a matching DC step sweep),
    return ``ron_sim`` directly.  Otherwise fall back to linear interpolation.
    """
    if (
        len(vin_ref) == len(vin_sim)
        and np.allclose(vin_ref, vin_sim, rtol=0.0, atol=1.0e-6)
    ):
        return ron_sim.astype(np.float64)
    return np.interp(vin_ref, vin_sim, ron_sim).astype(np.float64)


def read_ngspice_noise_wrdata(path: Path) -> dict[str, NDArray[np.float64]]:
    """Read ngspice ``wrdata`` from a channel-noise analysis.

    Supports merged ``frequency total`` output (4 columns with ``wr_singlescale``)
    or legacy thermal ``onoise_spectrum`` / ``inoise_spectrum`` columns.
    """
    table = np.loadtxt(path)
    if table.ndim == 1:
        table = table.reshape(1, -1)
    if table.shape[1] < 2:
        msg = f"Expected >= 2 columns in noise wrdata, got {table.shape[1]}."
        raise ValueError(msg)
    frequency_hz = table[:, 0].astype(np.float64)
    if table.shape[1] == 2:
        noise = table[:, 1].astype(np.float64)
        return {
            "frequency_hz": frequency_hz,
            "noise_v_per_sqrt_hz": noise,
            "onoise_v_per_sqrt_hz": noise,
            "inoise_v_per_sqrt_hz": noise,
        }
    if table.shape[1] in (3, 4):
        noise = table[:, -1].astype(np.float64)
        return {
            "frequency_hz": frequency_hz,
            "noise_v_per_sqrt_hz": noise,
            "onoise_v_per_sqrt_hz": noise,
            "inoise_v_per_sqrt_hz": noise,
        }
    return {
        "frequency_hz": frequency_hz,
        "noise_v_per_sqrt_hz": table[:, -1].astype(np.float64),
        "onoise_v_per_sqrt_hz": table[:, -2].astype(np.float64),
        "inoise_v_per_sqrt_hz": table[:, -1].astype(np.float64),
    }


def read_ngspice_parasitics_wrdata(path: Path) -> dict[str, float]:
    """Read scalar parasitic metrics from ngspice ``parasitics.raw``.

    ``wrdata`` stores each scalar vector as index/value pairs on one row.
    """
    table = np.loadtxt(path)
    if table.ndim == 1:
        table = table.reshape(1, -1)
    if table.shape[1] < 10:
        msg = f"Expected 10 columns in parasitics wrdata, got {table.shape[1]}."
        raise ValueError(msg)
    row = table[0]
    return {
        "q_inj_coulomb": float(row[1]),
        "v_inj_v": float(row[3]),
        "v_feedthrough_v": float(row[5]),
        "attenuation_db": float(row[7]),
        "dummy_reduction_pct": float(row[9]),
    }


def read_ngspice_dc_wrdata(path: Path) -> dict[str, NDArray[np.float64]]:
    """Read ngspice ``wrdata`` from DC analysis (vin, ron columns)."""
    table = np.loadtxt(path)
    if table.ndim == 1:
        table = table.reshape(1, -1)
    if table.shape[1] < 2:
        msg = f"Expected >= 2 columns in DC wrdata, got {table.shape[1]}."
        raise ValueError(msg)
    vin = table[:, 0].astype(np.float64)
    ron = np.abs(table[:, -1].astype(np.float64))
    return {"vin_v": vin, "ron_ohm": ron}


def write_noise_csv(
    path: Path,
    frequency_hz: NDArray[np.float64],
    noise_v_per_sqrt_hz: NDArray[np.float64],
) -> None:
    """Write noise spectrum CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.column_stack([frequency_hz, noise_v_per_sqrt_hz])
    np.savetxt(path, data, delimiter=",", header=",".join(NOISE_COLUMNS), comments="")
