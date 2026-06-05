"""Netlist expression helpers shared by ngspice and Spectre renderers."""

from __future__ import annotations

from switch_model.config import SwitchConfig, SwitchType


def switch_kind_id(cfg: SwitchConfig) -> int:
    """Return ``SWITCH_KIND`` integer for Verilog-A / netlist templates."""
    mapping = {
        SwitchType.NMOS: 0,
        SwitchType.PMOS: 1,
        SwitchType.CMOS: 2,
        SwitchType.NMOS_DUMMY: 3,
        SwitchType.BS: 4,
        SwitchType.BS_DUMMY: 5,
    }
    return mapping[cfg.switch_type]


def drive_voltages(cfg: SwitchConfig) -> tuple[float, float]:
    """Return (vclk, vclk_bar) for the configured switch topology."""
    if cfg.switch_type == SwitchType.PMOS:
        return cfg.vclk_low_v, cfg.vdd_v - cfg.vclk_low_v
    if cfg.switch_type == SwitchType.CMOS:
        return cfg.vclk_high_v, cfg.vclk_low_v
    return cfg.vclk_high_v, cfg.vclk_high_v


def ngspice_ron_probe_expr(cfg: SwitchConfig) -> str:
    """Return ngspice B-source voltage expression for Ron (ohm) vs Vin."""
    vclk, vclk_bar = drive_voltages(cfg)
    roff = cfg.roff_ohm
    kn = cfg.k_n
    kp = cfg.k_p
    ratio = cfg.ratio
    vth_n = cfg.vth_n_v
    vth_p = cfg.vth_p_v
    ron_bs = cfg.ron_bs_ohm

    nmos_g = (
        f"(V(clk)>{vth_n})*({kn}*{ratio}*max(V(clk)-V(in)-{vth_n},1e-9))"
        f" + (V(clk)<={vth_n})*{1.0 / roff}"
    )
    pmos_g = (
        f"(V(clk)-V(in)<{vth_p})*({kp}*{ratio}*max({vth_p}-(V(clk)-V(in)),1e-9))"
        f" + (V(clk)-V(in)>={vth_p})*{1.0 / roff}"
    )
    bs_g = f"(V(clk)>{vth_n})*{1.0 / ron_bs} + (V(clk)<={vth_n})*{1.0 / roff}"

    match cfg.switch_type:
        case SwitchType.NMOS | SwitchType.NMOS_DUMMY:
            g_expr = nmos_g
        case SwitchType.PMOS:
            g_expr = pmos_g
        case SwitchType.BS | SwitchType.BS_DUMMY:
            g_expr = bs_g
        case SwitchType.CMOS:
            # Parallel conductance: g = g_n + g_p (avoid division by zero).
            g_expr = (
                f"(({nmos_g}) + ({pmos_g.replace('V(clk)', 'V(clkbar)')}))"
            )
        case _:
            msg = f"Unsupported switch type: {cfg.switch_type}"
            raise ValueError(msg)

    return f"abs(1 / ({g_expr}))"
