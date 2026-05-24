# Technical Brief: Private 5G Edge-AI Capacity Console

> ▶ Executive dashboard: [obiedeh.github.io/private-5g-edge-telemetry/reports/dashboard.html](https://obiedeh.github.io/private-5g-edge-telemetry/reports/dashboard.html)  
> Portal: [obiedeh.github.io/private-5g-edge-telemetry/reports/index.html](https://obiedeh.github.io/private-5g-edge-telemetry/reports/index.html)  
> Source: [github.com/obiedeh/private-5g-edge-telemetry](https://github.com/obiedeh/private-5g-edge-telemetry)

## Executive summary

This repo tests a practical factory capacity question: how far can a private-5G-style AGV floor scale before a 20 ms p95 control-loop budget breaks?

The seeded manufacturing simulation stays under budget through 100 AGVs. The first tested unsafe expansion point is 120 AGVs. The pressure signal appears first in the assembly-zone edge GPU pool, not as a proven radio-only failure.

## Operational question

Can a factory expand its AGV fleet without violating a 20 ms p95 control-loop latency budget, and should the next capacity decision focus on radio capacity, edge GPU capacity, or zone-level workload balance?

## System scope

| Area | Scope |
|---|---|
| Primary scenario | Manufacturing AGV capacity over private-5G-style telemetry |
| Main KPI | Worst-cell hourly p95 latency |
| Decision threshold | 20 ms p95 control-loop budget |
| Bottleneck signal | Assembly-zone edge GPU saturation appears first |
| Evidence type | Seeded simulation, generated plots, deterministic reports, benchmarks |
| Secondary scenario | Pharma bioreactor anomaly as portability evidence only |

## What the pipeline does

1. Generates or ingests telemetry shaped like private 5G + edge AI operations.
2. Validates schema and quarantines malformed rows without crashing the pipeline.
3. Engineers latency, radio, edge-load, and quality signals.
4. Aggregates telemetry into scenario evidence.
5. Produces business-case reports, dashboard HTML, portal HTML, plots, benchmark files, and JSON artifacts.

## Key finding

| Finding | Evidence |
|---|---|
| Recommended simulated ceiling | 100 AGVs under the 20 ms p95 budget |
| First tested unsafe expansion | 120 AGVs crosses the budget |
| Latency at 100 AGVs | 18.39 ms p95 |
| Latency at 120 AGVs | 23.40 ms p95 |
| Zone pressure | Assembly carries the heaviest load and hits the saturation knee first |
| Budget sensitivity | 15 ms = 80 AGVs, 20 ms = 100 AGVs, 25 ms = 120 AGVs |

Full manufacturing evidence lives in [`reports/business_cases/manufacturing_agv_capacity.md`](reports/business_cases/manufacturing_agv_capacity.md) and [`reports/scenarios/manufacturing_agv/dashboard_summary.md`](reports/scenarios/manufacturing_agv/dashboard_summary.md).

## Validation evidence

| Evidence | Current artifact |
|---|---|
| Tests | Pytest suite runs through `make verify` |
| Lint/type checks | `ruff check .` and `mypy private5g_pipeline` |
| CI | Python 3.11 and 3.12 |
| Synthetic-generator throughput | 10,455 rows/sec |
| Schema quarantine throughput | 168,237 rows/sec at 5% corruption |
| End-to-end regeneration | 16.124 s for both scenarios, both business cases, and portal |
| Determinism | Byte-identical metrics JSON, SHA-256 verified |

Benchmark methodology and raw timings are in [`reports/benchmarks.md`](reports/benchmarks.md) and [`reports/benchmarks.json`](reports/benchmarks.json).

## Boundaries / what this is not

This is seeded simulation evidence. It is not live factory telemetry.

- Not a live private 5G deployment.
- Not vendor RAN integration.
- Not NVIDIA Aerial integration.
- Not MES/SCADA/PLC integration.
- Not a production safety certification artifact.
- Not proof of real AGV fleet behavior.

The pharma bioreactor case is a portability check. It shows the same telemetry pattern applied to another regulated operational context, but manufacturing AGV capacity remains the headline use case.

## Next engineering step

Run the same dashboard flow against measured telemetry from a real factory or lab setup. The first validation target should be live RAN KPIs plus edge GPU utilization and queueing data, because that is where the current seeded simulation points the capacity decision.
