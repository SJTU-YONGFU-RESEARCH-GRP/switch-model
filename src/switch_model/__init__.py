"""switch-model: configurable MOS switch behavioral models."""

from switch_model.config import (
    BenchSweepConfig,
    SwitchConfig,
    SwitchNoiseConfig,
    SwitchType,
)
from switch_model.model import (
    simulate_charge_injection,
    simulate_clock_feedthrough,
    simulate_noise,
    simulate_ron_sweep,
)
from switch_model.parasitics import ChargeInjectionMetrics, ClockFeedthroughMetrics
from switch_model.ron import RonMetrics

__all__ = [
    "BenchSweepConfig",
    "ChargeInjectionMetrics",
    "ClockFeedthroughMetrics",
    "RonMetrics",
    "SwitchConfig",
    "SwitchNoiseConfig",
    "SwitchType",
    "simulate_charge_injection",
    "simulate_clock_feedthrough",
    "simulate_noise",
    "simulate_ron_sweep",
]

__version__ = "0.1.0"
