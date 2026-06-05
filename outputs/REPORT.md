# switch-model — multi-engine comparison

- **Generated:** 2026-06-05 18:44:44 UTC
- **Engines compared:** python, ngspice

- **Spectre status:** excluded from comparison (all runs fell back to Python — source Cadence env and see `spectre/*/logs/spectre_ron_sweep.log`)

Peer engines implement the same Ron equations (see `docs/MODEL.md`):

| Engine | Implementation |
| --- | --- |
| `python` | Python macromodel |
| `ngspice` | Behavioral SPICE (B-source, same equations) |
| `spectre` | Verilog-A `configurable_switch.va` |

## Per-engine summaries

- [python](python/REPORT.md)
- [ngspice](ngspice/REPORT.md)
- [spectre](spectre/REPORT.md)

## Metric spread

| Switch | Metric | Spread % | Tol % | OK |
| --- | --- | --- | --- | --- |
| `nmos` | `ron.ron_at_vcm_ohm` | 0.00 | 2.0 | yes |
| `nmos` | `ron.linearity_error_pct` | 0.00 | 2.0 | yes |
| `nmos` | `noise.flicker_corner_hz` | 0.00 | 2.0 | yes |
| `nmos` | `noise.noise_at_1hz_v_per_sqrt_hz` | 0.00 | 2.0 | yes |
| `pmos` | `ron.ron_at_vcm_ohm` | 0.00 | 2.0 | yes |
| `pmos` | `ron.linearity_error_pct` | 0.00 | 2.0 | yes |
| `pmos` | `noise.flicker_corner_hz` | 0.00 | 2.0 | yes |
| `pmos` | `noise.noise_at_1hz_v_per_sqrt_hz` | 0.00 | 2.0 | yes |
| `cmos` | `ron.ron_at_vcm_ohm` | 0.01 | 2.0 | yes |
| `cmos` | `ron.linearity_error_pct` | 0.03 | 2.0 | yes |
| `cmos` | `noise.flicker_corner_hz` | 0.00 | 2.0 | yes |
| `cmos` | `noise.noise_at_1hz_v_per_sqrt_hz` | 0.00 | 2.0 | yes |
| `nmos_dummy` | `ron.ron_at_vcm_ohm` | 0.00 | 2.0 | yes |
| `nmos_dummy` | `ron.linearity_error_pct` | 0.00 | 2.0 | yes |
| `nmos_dummy` | `noise.flicker_corner_hz` | 0.00 | 2.0 | yes |
| `nmos_dummy` | `noise.noise_at_1hz_v_per_sqrt_hz` | 0.00 | 2.0 | yes |
| `bs` | `ron.ron_at_vcm_ohm` | 0.00 | 2.0 | yes |
| `bs` | `ron.linearity_error_pct` | 0.00 | 2.0 | yes |
| `bs` | `noise.flicker_corner_hz` | 0.00 | 2.0 | yes |
| `bs` | `noise.noise_at_1hz_v_per_sqrt_hz` | 0.00 | 2.0 | yes |
| `bs_dummy` | `ron.ron_at_vcm_ohm` | 0.00 | 2.0 | yes |
| `bs_dummy` | `ron.linearity_error_pct` | 0.00 | 2.0 | yes |
| `bs_dummy` | `noise.flicker_corner_hz` | 0.00 | 2.0 | yes |
| `bs_dummy` | `noise.noise_at_1hz_v_per_sqrt_hz` | 0.00 | 2.0 | yes |

**Overall:** PASS

## Figure gallery

![python/nmos — Ron vs Vin](python/nmos/ron_sweep.svg)

*python/nmos — Ron vs Vin*

![python/nmos — noise spectrum](python/nmos/noise_spectrum.svg)

*python/nmos — noise spectrum*

![python/nmos — parasitics](python/nmos/parasitics_summary.svg)

*python/nmos — parasitics*

![ngspice/nmos — Ron vs Vin](ngspice/nmos/ron_sweep.svg)

*ngspice/nmos — Ron vs Vin*

![ngspice/nmos — noise spectrum](ngspice/nmos/noise_spectrum.svg)

*ngspice/nmos — noise spectrum*

![ngspice/nmos — parasitics](ngspice/nmos/parasitics_summary.svg)

*ngspice/nmos — parasitics*

![spectre/nmos — Ron vs Vin](spectre/nmos/ron_sweep.svg)

*spectre/nmos — Ron vs Vin*

![spectre/nmos — noise spectrum](spectre/nmos/noise_spectrum.svg)

*spectre/nmos — noise spectrum*

![spectre/nmos — parasitics](spectre/nmos/parasitics_summary.svg)

*spectre/nmos — parasitics*

![python/pmos — Ron vs Vin](python/pmos/ron_sweep.svg)

*python/pmos — Ron vs Vin*

![python/pmos — noise spectrum](python/pmos/noise_spectrum.svg)

*python/pmos — noise spectrum*

![python/pmos — parasitics](python/pmos/parasitics_summary.svg)

*python/pmos — parasitics*

![ngspice/pmos — Ron vs Vin](ngspice/pmos/ron_sweep.svg)

*ngspice/pmos — Ron vs Vin*

![ngspice/pmos — noise spectrum](ngspice/pmos/noise_spectrum.svg)

*ngspice/pmos — noise spectrum*

![ngspice/pmos — parasitics](ngspice/pmos/parasitics_summary.svg)

*ngspice/pmos — parasitics*

![spectre/pmos — Ron vs Vin](spectre/pmos/ron_sweep.svg)

*spectre/pmos — Ron vs Vin*

![spectre/pmos — noise spectrum](spectre/pmos/noise_spectrum.svg)

*spectre/pmos — noise spectrum*

![spectre/pmos — parasitics](spectre/pmos/parasitics_summary.svg)

*spectre/pmos — parasitics*

![python/cmos — Ron vs Vin](python/cmos/ron_sweep.svg)

*python/cmos — Ron vs Vin*

![python/cmos — noise spectrum](python/cmos/noise_spectrum.svg)

*python/cmos — noise spectrum*

![python/cmos — parasitics](python/cmos/parasitics_summary.svg)

*python/cmos — parasitics*

![ngspice/cmos — Ron vs Vin](ngspice/cmos/ron_sweep.svg)

*ngspice/cmos — Ron vs Vin*

![ngspice/cmos — noise spectrum](ngspice/cmos/noise_spectrum.svg)

*ngspice/cmos — noise spectrum*

![ngspice/cmos — parasitics](ngspice/cmos/parasitics_summary.svg)

*ngspice/cmos — parasitics*

![spectre/cmos — Ron vs Vin](spectre/cmos/ron_sweep.svg)

*spectre/cmos — Ron vs Vin*

![spectre/cmos — noise spectrum](spectre/cmos/noise_spectrum.svg)

*spectre/cmos — noise spectrum*

![spectre/cmos — parasitics](spectre/cmos/parasitics_summary.svg)

*spectre/cmos — parasitics*

![python/nmos_dummy — Ron vs Vin](python/nmos_dummy/ron_sweep.svg)

*python/nmos_dummy — Ron vs Vin*

![python/nmos_dummy — noise spectrum](python/nmos_dummy/noise_spectrum.svg)

*python/nmos_dummy — noise spectrum*

![python/nmos_dummy — parasitics](python/nmos_dummy/parasitics_summary.svg)

*python/nmos_dummy — parasitics*

![ngspice/nmos_dummy — Ron vs Vin](ngspice/nmos_dummy/ron_sweep.svg)

*ngspice/nmos_dummy — Ron vs Vin*

![ngspice/nmos_dummy — noise spectrum](ngspice/nmos_dummy/noise_spectrum.svg)

*ngspice/nmos_dummy — noise spectrum*

![ngspice/nmos_dummy — parasitics](ngspice/nmos_dummy/parasitics_summary.svg)

*ngspice/nmos_dummy — parasitics*

![spectre/nmos_dummy — Ron vs Vin](spectre/nmos_dummy/ron_sweep.svg)

*spectre/nmos_dummy — Ron vs Vin*

![spectre/nmos_dummy — noise spectrum](spectre/nmos_dummy/noise_spectrum.svg)

*spectre/nmos_dummy — noise spectrum*

![spectre/nmos_dummy — parasitics](spectre/nmos_dummy/parasitics_summary.svg)

*spectre/nmos_dummy — parasitics*

![python/bs — Ron vs Vin](python/bs/ron_sweep.svg)

*python/bs — Ron vs Vin*

![python/bs — noise spectrum](python/bs/noise_spectrum.svg)

*python/bs — noise spectrum*

![python/bs — parasitics](python/bs/parasitics_summary.svg)

*python/bs — parasitics*

![ngspice/bs — Ron vs Vin](ngspice/bs/ron_sweep.svg)

*ngspice/bs — Ron vs Vin*

![ngspice/bs — noise spectrum](ngspice/bs/noise_spectrum.svg)

*ngspice/bs — noise spectrum*

![ngspice/bs — parasitics](ngspice/bs/parasitics_summary.svg)

*ngspice/bs — parasitics*

![spectre/bs — Ron vs Vin](spectre/bs/ron_sweep.svg)

*spectre/bs — Ron vs Vin*

![spectre/bs — noise spectrum](spectre/bs/noise_spectrum.svg)

*spectre/bs — noise spectrum*

![spectre/bs — parasitics](spectre/bs/parasitics_summary.svg)

*spectre/bs — parasitics*

![python/bs_dummy — Ron vs Vin](python/bs_dummy/ron_sweep.svg)

*python/bs_dummy — Ron vs Vin*

![python/bs_dummy — noise spectrum](python/bs_dummy/noise_spectrum.svg)

*python/bs_dummy — noise spectrum*

![python/bs_dummy — parasitics](python/bs_dummy/parasitics_summary.svg)

*python/bs_dummy — parasitics*

![ngspice/bs_dummy — Ron vs Vin](ngspice/bs_dummy/ron_sweep.svg)

*ngspice/bs_dummy — Ron vs Vin*

![ngspice/bs_dummy — noise spectrum](ngspice/bs_dummy/noise_spectrum.svg)

*ngspice/bs_dummy — noise spectrum*

![ngspice/bs_dummy — parasitics](ngspice/bs_dummy/parasitics_summary.svg)

*ngspice/bs_dummy — parasitics*

![spectre/bs_dummy — Ron vs Vin](spectre/bs_dummy/ron_sweep.svg)

*spectre/bs_dummy — Ron vs Vin*

![spectre/bs_dummy — noise spectrum](spectre/bs_dummy/noise_spectrum.svg)

*spectre/bs_dummy — noise spectrum*

![spectre/bs_dummy — parasitics](spectre/bs_dummy/parasitics_summary.svg)

*spectre/bs_dummy — parasitics*


Regenerate: `python scripts/compare_engines.py --output-root outputs`
