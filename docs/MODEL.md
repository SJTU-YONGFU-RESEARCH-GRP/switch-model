# MOS switch behavioral model reference

Deep modeling reference for **switch-model**, aligned with Zhou et al., *Flicker Noise Analysis on Chopper Amplifier*, IEEE NEWCAS 2021.

## Related documentation

- [bench_spec.md](bench_spec.md) — bench definitions and outputs
- [golden_metrics.yaml](golden_metrics.yaml) — optional reference targets
- [Flicker_Noise_Analysis_on_Chopper_Amplifier.pdf](Flicker_Noise_Analysis_on_Chopper_Amplifier.pdf) — primary reference (NEWCAS 2021)

## Citation

```bibtex
@inproceedings{zhou2021flicker,
  title={Flicker Noise Analysis on Chopper Amplifier},
  author={Zhou, Ting and Gao, Zhuo and Huang, Jiajie and Lu, Yewangqing and Chen, Mingyi and Li, Yongfu},
  booktitle={IEEE International New Circuits and Systems Conference (NEWCAS)},
  year={2021},
  doi={10.1109/NEWCAS50681.2021.9462742}
}
```

## Switch topologies

| Type | Enum | Paper label | Description |
| --- | --- | --- | --- |
| NMOS | `nmos` | NS | N-type switch, signal-dependent Ron |
| PMOS | `pmos` | — | P-type switch (complementary drive) |
| CMOS | `cmos` | TG | Transmission gate (NMOS \|\| PMOS) |
| NMOS dummy | `nmos_dummy` | NS-D | NMOS with dummy for charge steering |
| Bootstrapped | `bs` | BS | Constant Ron (bootstrap) |
| BS dummy | `bs_dummy` | BS + dummy | Bootstrapped with dummy switch |

## On-resistance (paper Fig. 3)

**NMOS (on):**

\[
R_{on} = \frac{1}{K \cdot \mathrm{Ratio} \cdot (V_{clk} - V_{in} - V_{th,n})}
\]

**PMOS (on):**

\[
R_{on} = \frac{1}{K_p \cdot \mathrm{Ratio} \cdot (V_{in} - V_{clk} - |V_{th,p}|)}
\]

**CMOS / TG:**

\[
R_{on,TG} = R_{on,n} \parallel R_{on,p}
\]

**Bootstrapped (BS):** constant `ron_bs_ohm` when \(V_{clk} > V_{th,n}\).

Implementation: `src/switch_model/ron.py`, Verilog-A `veriloga/configurable_switch.va`.

## Channel noise (paper Fig. 3)

Coram-corrected flicker with thermal noise on the channel resistance:

\[
I_r = \frac{V_{in} - V_{out}}{R_{on}}
\qquad
P_n = K_F \cdot |I_r|^{A_F}
\]

\[
e_n(f) = \sqrt{4 k T R_{on} + \frac{e_{n,\mathrm{flicker@1Hz}}^2}{f^{E_F}}}
\]

Implementation: `src/switch_model/noise.py`.

## Parasitic non-idealities (paper Fig. 1)

| Effect | Model | Parameters |
| --- | --- | --- |
| Charge injection | \(Q_{inj} = (C_{gs}+C_{gd})\,\Delta V_{clk}\) | `cgs_f`, `cgd_f`; dummy reduces by `dummy_charge_split` |
| Clock feedthrough | \(V_{cf} = \frac{C_{gd}}{C_{gd}+C_{load}}\,\Delta V_{clk}\) | `cgd_f`, `cp1_f`, `cp2_f`, `c_load_f` |
| CMOS mismatch | Parasitic scale \((1 + \mathrm{clock\_mismatch\_ratio})\) | Table I sweep range |

Implementation: `src/switch_model/parasitics.py`.

## Verilog-A modules

| Module | Path | SWITCH_KIND |
| --- | --- | --- |
| Base | `veriloga/configurable_switch.va` | 0–5 parameter |
| NMOS | `veriloga/configurable_nmos_switch.va` | 0 |
| PMOS | `veriloga/configurable_pmos_switch.va` | 1 |
| CMOS (TG) | `veriloga/configurable_cmos_switch.va` | 2 |
| NMOS dummy | `veriloga/configurable_nmos_dummy_switch.va` | 3 |
| BS | `veriloga/configurable_bs_switch.va` | 4 |
| BS dummy | `veriloga/configurable_bs_dummy_switch.va` | 5 |

## Python API

```python
from switch_model import SwitchConfig, SwitchType, simulate_ron_sweep, simulate_noise

cfg = SwitchConfig(switch_type=SwitchType.BS, fch_hz=2.0e3)
ron = simulate_ron_sweep(cfg)
noise = simulate_noise(cfg)
```

Default parasitic caps: 25 fF (paper Table I). Default chopping frequency: 2 kHz.
