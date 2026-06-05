"""Matplotlib plotting helpers for switch benches."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray


def plot_ron_sweep(
    vin_v: NDArray[np.float64],
    ron_ohm: NDArray[np.float64],
    path: Path,
    *,
    title: str,
    switch_type: str,
) -> None:
    """Plot Ron versus Vin and save SVG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(vin_v, ron_ohm, linewidth=2.0)
    ax.set_xlabel("Vin (V)")
    ax.set_ylabel("Ron (Ω)")
    ax.set_title(f"{title} ({switch_type})")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, format="svg")
    plt.close(fig)


def plot_noise_spectrum(
    frequency_hz: NDArray[np.float64],
    noise_v_per_sqrt_hz: NDArray[np.float64],
    path: Path,
    *,
    title: str,
    flicker_corner_hz: float,
) -> None:
    """Plot noise spectrum and save SVG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.loglog(frequency_hz, noise_v_per_sqrt_hz * 1.0e9, linewidth=2.0)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Noise (nV/√Hz)")
    ax.set_title(title)
    if np.isfinite(flicker_corner_hz):
        label = f"fc={flicker_corner_hz:.1f} Hz"
        ax.axvline(flicker_corner_hz, color="r", linestyle="--", label=label)
        ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, format="svg")
    plt.close(fig)
