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

## Testbench netlists (planned)

| Engine | Path | Status |
| --- | --- | --- |
| ngspice | `testbench/ngspice/ron_sweep.cir` | Scaffold |
| spectre | `testbench/spectre/ron_sweep.scs` | Scaffold |

Python engine is fully implemented; SPICE/Spectre decks reference `veriloga/configurable_switch.va`.
