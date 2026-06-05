# switch-model

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-green?logo=creativecommons&logoColor=white)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776ab.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](.)

Configurable **MOS switch** behavioral models with Python and Verilog-A, following the chopper-amplifier switch analysis in Zhou et al., *Flicker Noise Analysis on Chopper Amplifier*, IEEE NEWCAS 2021.

The paper is included under [docs/](docs/Flicker_Noise_Analysis_on_Chopper_Amplifier.pdf) for citation in this repository.

## Features

| Area | What is included |
| --- | --- |
| **Switch types** | NMOS, PMOS, CMOS (TG), NMOS+dummy, bootstrapped (BS), BS+dummy |
| **Non-idealities** | Signal-dependent Ron, thermal + flicker noise, charge injection, clock feedthrough |
| **Engines** | `python` (full), `ngspice` (behavioral SPICE, same Ron equations), `spectre` (Verilog-A) |
| **Benches** | Ron sweep, noise spectrum, parasitics, cross-type comparison |

## Installation

```bash
cd switch-model
./scripts/install_python.sh
source .venv/bin/activate
pytest
```

## Quick start

```bash
# NMOS Ron sweep
python scripts/run_ron.py --switch-type nmos --output-dir outputs/python/nmos

# Bootstrapped switch noise
python scripts/run_noise.py --switch-type bs --output-dir outputs/python/bs

# Compare all six topologies
python scripts/run_compare_switches.py

# Run all engines (python + ngspice + spectre) and compare
./scripts/run_all_simulations.sh --skip-missing
# Per-engine: outputs/<engine>/REPORT.md
# Cross-engine: outputs/REPORT.md
```

## Python API

```python
from switch_model import SwitchConfig, SwitchType, simulate_ron_sweep, simulate_noise

cfg = SwitchConfig(switch_type=SwitchType.CMOS, cgs_f=50e-15, fch_hz=2e3)
ron = simulate_ron_sweep(cfg)
noise = simulate_noise(cfg)
```

## Project layout

```text
switch-model/
├── docs/                  # MODEL.md, paper PDF, golden_metrics.yaml
├── veriloga/              # configurable_switch.va + type wrappers
├── src/switch_model/      # Python package
├── scripts/               # run_ron.py, run_noise.py, run_parasitics.py, …
├── testbench/             # ngspice / spectre scaffolds
└── tests/
```

## Citation

If you use this work, please cite:

> T. Zhou, Z. Gao, J. Huang, Y. Lu, M. Chen, and Y. Li, "Flicker Noise Analysis on Chopper Amplifier," in *Proc. IEEE Int. New Circuits and Systems Conf. (NEWCAS)*, 2021. DOI: [10.1109/NEWCAS50681.2021.9462742](https://doi.org/10.1109/NEWCAS50681.2021.9462742)

BibTeX and modeling equations: [docs/MODEL.md](docs/MODEL.md).

## License

CC BY 4.0 — see [LICENSE](LICENSE). Copyright (c) 2026 SJTU-YONGFU-RESEARCH-GRP.
