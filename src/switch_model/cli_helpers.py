"""Shared CLI helpers for switch-model testbench scripts."""

from __future__ import annotations

import argparse

from switch_model.config import SwitchConfig, SwitchNoiseConfig, SwitchType


def add_switch_args(parser: argparse.ArgumentParser) -> None:
    """Register core switch macromodel arguments."""
    parser.add_argument(
        "--switch-type",
        type=str,
        default="nmos",
        choices=[t.value for t in SwitchType],
        help="Switch topology (nmos, pmos, cmos, nmos_dummy, bs, bs_dummy).",
    )
    parser.add_argument("--vdd-v", type=float, default=1.8, help="Supply voltage (V).")
    parser.add_argument("--vth-n-v", type=float, default=0.4, help="NMOS threshold (V).")
    parser.add_argument("--vth-p-v", type=float, default=-0.4, help="PMOS threshold (V).")
    parser.add_argument("--k-n", type=float, default=2.0e-5, help="NMOS conductance factor.")
    parser.add_argument("--k-p", type=float, default=1.5e-5, help="PMOS conductance factor.")
    parser.add_argument("--ratio", type=float, default=10.0, help="W/L aspect ratio factor.")
    parser.add_argument("--ron-bs-ohm", type=float, default=200.0, help="BS constant Ron (ohm).")
    parser.add_argument("--roff-ohm", type=float, default=1.0e12, help="Off resistance (ohm).")
    parser.add_argument("--fch-hz", type=float, default=2.0e3, help="Chopping frequency (Hz).")
    parser.add_argument("--cgs-f", type=float, default=25.0e-15, help="Cgs parasitic (F).")
    parser.add_argument("--cgd-f", type=float, default=25.0e-15, help="Cgd parasitic (F).")
    parser.add_argument("--cp1-f", type=float, default=25.0e-15, help="Cp1 parasitic (F).")
    parser.add_argument("--cp2-f", type=float, default=25.0e-15, help="Cp2 parasitic (F).")
    parser.add_argument("--c-load-f", type=float, default=1.0e-12, help="Load capacitance (F).")
    parser.add_argument(
        "--clock-mismatch-ratio",
        type=float,
        default=0.0,
        help="CMOS parasitic mismatch ratio (0-1).",
    )
    parser.add_argument(
        "--dummy-charge-split",
        type=float,
        default=0.5,
        help="Fraction of charge steered to dummy switch.",
    )


def add_noise_args(parser: argparse.ArgumentParser) -> None:
    """Register noise arguments."""
    parser.add_argument(
        "--no-noise",
        action="store_true",
        help="Disable channel noise sources.",
    )
    parser.add_argument(
        "--en-white-nv-per-sqrt-hz",
        type=float,
        default=0.0,
        dest="en_white_nv",
        help="White noise (nV/sqrt(Hz)); 0 derives from Ron.",
    )
    parser.add_argument(
        "--en-flicker-1hz-nv-per-sqrt-hz",
        type=float,
        default=50.0,
        dest="en_flicker_1hz_nv",
        help="Flicker density at 1 Hz (nV/sqrt(Hz)).",
    )
    parser.add_argument("--en-flicker-ef", type=float, default=1.0, help="Flicker exponent EF.")
    parser.add_argument("--kf", type=float, default=1.0e-24, help="Coram KF coefficient.")
    parser.add_argument("--af", type=float, default=1.0, help="Coram AF exponent.")


def add_output_args(parser: argparse.ArgumentParser) -> None:
    """Register output directory argument."""
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/python",
        help="Directory for CSV, SVG, and metrics JSON.",
    )


def build_noise_config(args: argparse.Namespace) -> SwitchNoiseConfig:
    """Build noise config from parsed CLI arguments."""
    return SwitchNoiseConfig(
        en_white_v_per_sqrt_hz=args.en_white_nv * 1.0e-9,
        en_flicker_1hz_v_per_sqrt_hz=args.en_flicker_1hz_nv * 1.0e-9,
        en_flicker_ef=args.en_flicker_ef,
        kf=args.kf,
        af=args.af,
        enable_noise=not args.no_noise,
    )


def build_switch_config(args: argparse.Namespace) -> SwitchConfig:
    """Build switch config from parsed CLI arguments."""
    noise = build_noise_config(args)
    return SwitchConfig(
        switch_type=SwitchType(args.switch_type),
        vdd_v=args.vdd_v,
        vth_n_v=args.vth_n_v,
        vth_p_v=args.vth_p_v,
        k_n=args.k_n,
        k_p=args.k_p,
        ratio=args.ratio,
        ron_bs_ohm=args.ron_bs_ohm,
        roff_ohm=args.roff_ohm,
        fch_hz=args.fch_hz,
        cgs_f=args.cgs_f,
        cgd_f=args.cgd_f,
        cp1_f=args.cp1_f,
        cp2_f=args.cp2_f,
        c_load_f=args.c_load_f,
        clock_mismatch_ratio=args.clock_mismatch_ratio,
        dummy_charge_split=args.dummy_charge_split,
        noise=noise,
    )
