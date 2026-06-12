"""Configuration dataclasses for MOS switch macromodels."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class SwitchType(str, Enum):
    """Supported switch topologies from Zhou et al., NEWCAS 2021."""

    NMOS = "nmos"
    PMOS = "pmos"
    CMOS = "cmos"
    NMOS_DUMMY = "nmos_dummy"
    PMOS_DUMMY = "pmos_dummy"
    CMOS_DUMMY = "cmos_dummy"
    BS = "bs"
    BS_DUMMY = "bs_dummy"


@dataclass(frozen=True)
class BenchSweepConfig:
    """Log-spaced frequency or voltage sweep defaults."""

    f_start_hz: float = 1.0
    f_stop_hz: float = 1.0e6
    points_per_decade: int = 10
    vin_start_v: float = 0.0
    vin_stop_v: float = 1.8
    vin_points: int = 50

    @property
    def num_decades(self) -> float:
        """Return number of frequency decades in the sweep."""
        if self.f_start_hz <= 0.0 or self.f_stop_hz <= 0.0:
            return 0.0
        return math.log10(self.f_stop_hz / self.f_start_hz)


@dataclass(frozen=True)
class SwitchNoiseConfig:
    """Channel thermal and flicker noise (Coram-corrected, paper Fig. 3)."""

    en_white_v_per_sqrt_hz: float = 0.0
    en_flicker_1hz_v_per_sqrt_hz: float = 50.0e-9
    en_flicker_ef: float = 1.0
    kf: float = 1.0e-24
    af: float = 1.0
    temperature_k: float = 300.0
    enable_noise: bool = True

    @property
    def thermal_from_ron(self) -> bool:
        """Return True when white noise is derived from channel resistance."""
        return self.en_white_v_per_sqrt_hz <= 0.0


@dataclass(frozen=True)
class SwitchConfig:
    """Small-signal and parasitic parameters for MOS switches."""

    switch_type: SwitchType = SwitchType.NMOS
    vth_n_v: float = 0.4
    vth_p_v: float = -0.4
    k_n: float = 2.0e-5
    k_p: float = 1.5e-5
    ratio: float = 10.0
    ron_bs_ohm: float = 200.0
    roff_ohm: float = 1.0e12
    vdd_v: float = 1.8
    vss_v: float = 0.0
    vclk_high_v: float = 1.8
    vclk_low_v: float = 0.0
    fch_hz: float = 2.0e3
    cgs_f: float = 25.0e-15
    cgd_f: float = 25.0e-15
    cp1_f: float = 25.0e-15
    cp2_f: float = 25.0e-15
    cgs_dummy_f: float = 25.0e-15
    cgd_dummy_f: float = 25.0e-15
    cp1_dummy_f: float = 25.0e-15
    cp2_dummy_f: float = 25.0e-15
    dummy_charge_split: float = 0.5
    clock_mismatch_ratio: float = 0.0
    clock_edge_skew_s: float = 0.0
    c_load_f: float = 1.0e-12
    noise: SwitchNoiseConfig = field(default_factory=SwitchNoiseConfig)
    sweep: BenchSweepConfig = field(default_factory=BenchSweepConfig)

    def effective_parasitic_caps(self) -> dict[str, float]:
        """Return total parasitic capacitances including dummy contributions."""
        caps = {
            "cgs_f": self.cgs_f,
            "cgd_f": self.cgd_f,
            "cp1_f": self.cp1_f,
            "cp2_f": self.cp2_f,
        }
        if self.switch_type in (
            SwitchType.NMOS_DUMMY,
            SwitchType.PMOS_DUMMY,
            SwitchType.CMOS_DUMMY,
            SwitchType.BS_DUMMY,
        ):
            caps["cgs_f"] += self.cgs_dummy_f
            caps["cgd_f"] += self.cgd_dummy_f
            caps["cp1_f"] += self.cp1_dummy_f
            caps["cp2_f"] += self.cp2_dummy_f
        if self.switch_type in (SwitchType.CMOS, SwitchType.CMOS_DUMMY):
            caps["cgs_f"] *= 1.0 + self.clock_mismatch_ratio
            caps["cgd_f"] *= 1.0 + self.clock_mismatch_ratio
            caps["cp1_f"] *= 1.0 + self.clock_mismatch_ratio
            caps["cp2_f"] *= 1.0 + self.clock_mismatch_ratio
        return caps
