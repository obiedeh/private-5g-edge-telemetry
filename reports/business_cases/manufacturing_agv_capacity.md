# Manufacturing AGV-fleet capacity — business case

For the ops lead asking how far the AGV fleet can grow before the line starts
missing vision deadlines. The deployment shape: private 5G in the plant, edge AI
doing per-AGV vision, and an ops team that needs a defensible fleet number. The
telemetry pattern is the same whether the wireless is Ericsson or Nokia, whether
the inference runs on NVIDIA or Qualcomm silicon, whether the automation layer is
Siemens or Rockwell. The bottleneck under fleet growth is the edge GPU pool, not
the radio. This document is the answer.

## What we asked

Can the floor add more AGVs without breaking the 20 ms
vision control-loop budget?

## What we found

**100 AGVs.** That's the largest fleet that keeps the worst
cell's hourly p95 latency at or below 20 ms. Past that, the
assembly-zone cell's GPU pool saturates first — it's the busiest zone, so
it runs out of inference headroom before paint or warehouse do — and
latency climbs into budget-breach territory.

![Worst-cell latency vs fleet size](../scenarios/manufacturing_agv/figures/01_latency_vs_fleet.png)

Blue bars stay under the dashed 20 ms budget line; red bars are over.

## Sensitivity

### If you change the budget

Tighter deadlines mean fewer AGVs. Looser deadlines mean more.

| Latency budget | Max fleet under budget |
|---:|---:|
| 15 ms | 80 |
| 20 ms | 100 |
| 25 ms | 120 |

### Where exactly does the budget break?

Stepping through fleet size in fine increments around the crossover:

| Fleet size | Worst-cell p95 latency (ms) | Budget |
|---:|---:|:---|
| 80 | 13.76 | ok |
| 90 | 16.54 | ok |
| 95 | 17.60 | ok |
| 100 | 19.96 | ok |
| 105 | 20.65 | over |
| 110 | 21.82 | over |
| 120 | 23.14 | over |

The crossover sits between the last *ok* row and the first *over* row.

### Is the answer noise?

We re-ran the default sweep at three other seeds to find out.

| Seed | Max fleet under budget |
|---:|---:|
| 42 | 100 |
| 7 | 100 |
| 17 | 100 |
| 99 | 100 |

The same number every time. The answer is the model, not the noise.

![Edge GPU load by zone](../scenarios/manufacturing_agv/figures/02_edge_load_by_zone.png)

The middle plot shows why assembly hits the wall first — it carries 42% of the
fleet, so its cell's edge GPU load crosses the saturation knee well before paint
(34%) or warehouse (24%) do.

## What we tested, what we didn't

Every number here comes from a seeded simulation calibrated to a plausible
edge-AI vision workload. We didn't connect to a live RAN, a vendor edge
platform, or any specific factory's telemetry. Real measured data would
shift the GPU-load-per-AGV coefficient, the saturation knee, and the
post-saturation latency slope. What stays portable is the shape — there's a
fleet size beyond which the budget breaks, and you find it by sweeping.

## Linked evidence

- Scenario dashboard: [`reports/scenarios/manufacturing_agv/dashboard_summary.md`](../scenarios/manufacturing_agv/dashboard_summary.md)
- Raw sensitivity numbers: [`manufacturing_agv_sensitivity.json`](manufacturing_agv_sensitivity.json)
