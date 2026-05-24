# Pharma bioreactor anomaly detection — business case

For the QA lead asking how fast a contamination event gets flagged, and
how noisy the detector is during the rest of the shift.

## What we asked

When a contamination event starts, how fast does the detector catch it,
and how clean is its precision across the calm hours of the day?

## What we found

At z = 3.0 on the edge-load × latency signal, with a
trailing 1-hour baseline and a 10-minute gap before the test sample, the
detector fires **5 min after onset** on `cell_pha_001`. Precision across the
full 24-hour day is **1.00** — no
false positives in the drift hours.

![Detector z-score across the day](../scenarios/pharma_bioreactor/figures/02_detector_zscore.png)

Z-score sits in the noise band through the drift hours, then spikes at the event
window (red band) above the z=3.0 threshold (blue dashed line).

## Sensitivity

### If you change the threshold

Loosen z and the detector picks up drift noise. Tighten it and precision
stays clean without sacrificing lead time on this signal.

| z-threshold | Detected | Lead time | TP windows | FP windows | Precision |
|---:|:---:|---:|---:|---:|---:|
| 2.0 | yes | 5 min | 4 | 3 | 0.57 |
| 2.5 | yes | 5 min | 3 | 2 | 0.60 |
| 3.0 | yes | 5 min | 3 | 0 | 1.00 |
| 3.5 | yes | 5 min | 2 | 0 | 1.00 |
| 4.0 | yes | 5 min | 2 | 0 | 1.00 |

### Is the answer noise?

We re-ran the same configuration at four seeds.

| Seed | Detected | Lead time | TP windows | FP windows | Precision |
|---:|:---:|---:|---:|---:|---:|
| 42 | yes | 5 min | 3 | 0 | 1.00 |
| 7 | yes | 5 min | 3 | 0 | 1.00 |
| 17 | yes | 5 min | 3 | 0 | 1.00 |
| 99 | yes | 5 min | 3 | 0 | 1.00 |

Lead time across seeds: 5–5 min. Precision across seeds: 1.00–1.00.
The 5-minute / 1.00 result holds.

![Lead time vs precision across threshold sweep](../scenarios/pharma_bioreactor/figures/03_threshold_sweep.png)

Blue: lead time. Red: precision. Threshold rises along the x-axis. Lead time stays
flat at 5 min; precision climbs from 0.57 to 1.00 as the threshold tightens.

## What we tested, what we didn't

Every number here comes from a seeded simulation with one injected
~75-minute contamination event on `cleanroom_A`. We didn't connect to a real
cleanroom, an MES, or any vendor's computer-vision model. Real measured data
would shift the drift rates, the event signature amplitude, and the right
baseline window length. What stays portable is the shape — *threshold trades
false-positive cost against lead time, and a gap in the baseline keeps a
fresh spike from poisoning its own σ*.

## Linked evidence

- Scenario dashboard: [`reports/scenarios/pharma_bioreactor/dashboard_summary.md`](../scenarios/pharma_bioreactor/dashboard_summary.md)
- Raw sensitivity numbers: [`pharma_bioreactor_sensitivity.json`](pharma_bioreactor_sensitivity.json)
