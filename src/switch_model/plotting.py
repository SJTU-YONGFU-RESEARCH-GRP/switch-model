"""Matplotlib plotting helpers for switch benches."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from switch_model.parasitics import ChargeInjectionMetrics, ClockFeedthroughMetrics


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


def plot_parasitics_summary(
    charge: ChargeInjectionMetrics,
    feedthrough: ClockFeedthroughMetrics,
    path: Path,
    *,
    title: str,
    switch_type: str,
) -> None:
    """Plot parasitic charge and voltage metrics as bar charts and save SVG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax_chg, ax_volt) = plt.subplots(1, 2, figsize=(10, 5))

    charge_labels = ("Cgs", "Cgd", "Q total")
    charge_fc = (
        charge.cgs_contribution_c * 1.0e15,
        charge.cgd_contribution_c * 1.0e15,
        charge.q_inj_coulomb * 1.0e15,
    )
    ax_chg.bar(charge_labels, charge_fc, color="#0033cc", edgecolor="#002080", linewidth=1.0)
    ax_chg.set_ylabel("Charge (fC)")
    ax_chg.set_title("Charge injection")
    ax_chg.grid(True, axis="y", alpha=0.3)

    volt_labels = ("V_inj", "V_cf")
    volt_mv = (charge.v_inj_v * 1.0e3, feedthrough.v_feedthrough_v * 1.0e3)
    ax_volt.bar(volt_labels, volt_mv, color="#7f3fbf", edgecolor="#5a2d8a", linewidth=1.0)
    ax_volt.set_ylabel("Voltage (mV)")
    ax_volt.set_title("Injection and feedthrough")
    ax_volt.grid(True, axis="y", alpha=0.3)
    if charge.dummy_reduction_pct > 0.0:
        ax_volt.text(
            0.98,
            0.95,
            f"Dummy reduction: {charge.dummy_reduction_pct:.1f} %",
            transform=ax_volt.transAxes,
            ha="right",
            va="top",
            fontsize=9,
        )

    fig.suptitle(f"{title} ({switch_type})")
    fig.tight_layout()
    fig.savefig(path, format="svg")
    plt.close(fig)
