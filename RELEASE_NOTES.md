# Release Notes

## v1.0.0 - Private 5G edge-AI telemetry evidence pack

This release marks the repo as a portfolio-complete static evidence pack for the manufacturing AGV capacity question.

### Evidence included

- Executive dashboard and visual portal for the AGV fleet capacity decision.
- Manufacturing business case showing 100 AGVs under the 20 ms p95 budget and 120 AGVs over budget.
- Bottleneck attribution pointing to assembly-zone edge GPU saturation in the seeded simulation.
- Schema validation and quarantine evidence.
- Pipeline benchmarks for synthetic generation, quarantine throughput, regeneration time, and deterministic output.
- Secondary pharma bioreactor scenario retained as portability evidence only.

### Boundary

This release does not claim live private 5G deployment, vendor RAN integration, NVIDIA Aerial integration, MES/SCADA/PLC integration, measured factory telemetry, production deployment, or safety certification.

### Release command

If publishing a Git tag, use:

```bash
git tag -a v1.0.0 -m "Release v1.0.0: private 5G edge AI telemetry evidence pack"
git push origin v1.0.0
```

## v0.1.0

- Added a reproducible `make demo` path that writes a full artifact bundle under `data/demo/`.
- Added fail-soft schema handling with quarantine output for invalid rows.
- Added publishable visual insights with raw-vs-curated and throughput-vs-latency figures.
- Added richer radio telemetry fields and a handover-vs-latency operator chart.
- Added an artifact index for demo outputs and a walkthrough for telecom-oriented review.
