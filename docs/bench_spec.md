# Bench specifications

## Benches

| Script | Purpose | Outputs |
| --- | --- | --- |
| `scripts/run_ron.py` | Ron vs Vin (signal dependence) | `ron_sweep.csv`, `ron_sweep.svg`, `RON_REPORT.md` |
| `scripts/run_noise.py` | Channel noise spectrum | `noise_spectrum.csv`, `noise_spectrum.svg`, `NOISE_REPORT.md` |
| `scripts/run_parasitics.py` | Charge injection + clock feedthrough | `switch_metrics.json` |
| `scripts/run_compare_switches.py` | All six topologies | `switch_comparison.json` |
| `scripts/run_all_simulations.sh` | Batch all types + summary | `outputs/python/REPORT.md` |
| `scripts/write_summary_report.py` | Regenerate summary from artifacts | `outputs/python/REPORT.md` |

## Metrics (`switch_metrics.json`)

| Key | Unit | Description |
| --- | --- | --- |
| `ron.ron_min_ohm` | Ω | Minimum Ron in Vin sweep |
| `ron.ron_max_ohm` | Ω | Maximum Ron in Vin sweep |
| `ron.linearity_error_pct` | % | (Ron_max − Ron_min) / Ron_BS |
| `noise.flicker_corner_hz` | Hz | Thermal/flicker equality frequency |
| `charge_injection.v_inj_v` | V | Equivalent injection step |
| `clock_feedthrough.v_feedthrough_v` | V | Feedthrough step at output |

## Engines

| Engine | Ron | Noise | Implementation |
| --- | --- | --- | --- |
| `python` | Full | Full | `src/switch_model/` macromodel |
| `ngspice` | Full | Python-backed | `testbench/ngspice/ron_sweep.cir` (behavioral B-source) |
| `spectre` | VA + PSF | Python-backed | `testbench/spectre/ron_sweep.scs` + `veriloga/configurable_switch.va` |

ngspice uses **behavioral SPICE** with the same Ron equations as Python/VA (native Verilog-A is not required in ngspice). Spectre runs the **Verilog-A** module when a license is available.

## Cross-engine comparison

```bash
./scripts/run_all_simulations.sh --skip-missing
python scripts/compare_engines.py --output-root outputs
```

Writes `outputs/REPORT.md` with per-engine links and metric spread table.
