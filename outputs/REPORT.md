# switch-model — multi-engine comparison

- **Generated:** 2026-06-05 09:48:51 UTC
- **Engines:** python, ngspice, spectre

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
| `nmos` | `ron.ron_at_vcm_ohm` | 0.00 | 5.0 | yes |
| `nmos` | `ron.linearity_error_pct` | 0.00 | 10.0 | yes |
| `nmos` | `noise.flicker_corner_hz` | 0.00 | 10.0 | yes |
| `pmos` | `ron.ron_at_vcm_ohm` | 100.00 | 5.0 | **NO** |
| `pmos` | `ron.linearity_error_pct` | 100.00 | 10.0 | **NO** |
| `cmos` | `ron.ron_at_vcm_ohm` | 0.01 | 5.0 | yes |
| `cmos` | `ron.linearity_error_pct` | 0.03 | 10.0 | yes |
| `cmos` | `noise.flicker_corner_hz` | 0.00 | 10.0 | yes |
| `nmos_dummy` | `ron.ron_at_vcm_ohm` | 0.00 | 5.0 | yes |
| `nmos_dummy` | `ron.linearity_error_pct` | 0.00 | 10.0 | yes |
| `nmos_dummy` | `noise.flicker_corner_hz` | 0.00 | 10.0 | yes |
| `bs` | `ron.ron_at_vcm_ohm` | 0.00 | 5.0 | yes |
| `bs` | `ron.linearity_error_pct` | 0.00 | 10.0 | yes |
| `bs` | `noise.flicker_corner_hz` | 0.00 | 10.0 | yes |
| `bs_dummy` | `ron.ron_at_vcm_ohm` | 0.00 | 5.0 | yes |
| `bs_dummy` | `ron.linearity_error_pct` | 0.00 | 10.0 | yes |
| `bs_dummy` | `noise.flicker_corner_hz` | 0.00 | 10.0 | yes |

**Overall:** FAIL

Regenerate: `python scripts/compare_engines.py --output-root outputs`
