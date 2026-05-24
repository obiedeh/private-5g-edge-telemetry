# Business Case: Private 5G Edge-AI AGV Capacity Planning

## Decision Question

Can a factory expand AGV fleet size without violating a 20 ms p95 control-loop latency budget?

## Operational Risk

Fleet growth increases edge inference demand, zone-level queueing, and worst-cell latency before the radio layer may appear to fail.

## What I Built

I built a reproducible telemetry-intelligence pipeline that joins private-5G-style KPIs, AGV fleet load, edge GPU pressure, schema validation, quarantine behavior, deterministic simulation, benchmark evidence, and a static decision dashboard.

## Finding

The simulated floor stayed under budget through 100 AGVs. At 120 AGVs, the 20 ms budget broke.

## Bottleneck

Assembly-zone edge GPU saturation appeared first in the simulation.

## Recommendation

Cap expansion at 100 AGVs, rebalance assembly-zone workload, reserve edge GPU capacity before testing 120 AGVs, and validate with live RAN and GPU telemetry before deployment.

## Business Value

Avoid expanding into unsafe latency margins and avoid buying the wrong capacity layer first.

## Boundaries

Seeded simulation only. No live private 5G network, vendor RAN integration, MES/SCADA/PLC connection, production deployment, or safety certification.
