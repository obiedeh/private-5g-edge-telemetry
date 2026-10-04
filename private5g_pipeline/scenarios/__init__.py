"""Vertical scenario generators for the private 5G + edge-AI telemetry pipeline.

Each scenario:
    * generates schema-conformant raw telemetry that mimics a named edge-AI
      operational situation (manufacturing AGV-fleet, pharma bioreactor),
    * runs the standard `qc_and_cast → engineer_features →
      aggregate_hourly_per_cell_slice` chain over it,
    * computes a scenario-specific operational metric (latency-budget
      capacity, anomaly-detection lead time),
    * writes a self-contained evidence pack under
      ``reports/scenarios/<vertical>/``.

The scenarios are intentionally deterministic (seeded numpy RNG) so the
committed evidence packs round-trip byte-identically across re-runs.
"""

from __future__ import annotations

from private5g_pipeline.scenarios.manufacturing import (
    DEFAULT_LATENCY_BUDGET_MS,
    run_manufacturing_agv_scenario,
)
from private5g_pipeline.scenarios.manufacturing import (
    DEFAULT_OUTPUT_DIR as MANUFACTURING_DEFAULT_OUTPUT_DIR,
)
from private5g_pipeline.scenarios.pharma import (
    DEFAULT_OUTPUT_DIR as PHARMA_DEFAULT_OUTPUT_DIR,
)
from private5g_pipeline.scenarios.pharma import (
    run_pharma_bioreactor_scenario,
)

__all__ = [
    "DEFAULT_LATENCY_BUDGET_MS",
    "MANUFACTURING_DEFAULT_OUTPUT_DIR",
    "PHARMA_DEFAULT_OUTPUT_DIR",
    "run_manufacturing_agv_scenario",
    "run_pharma_bioreactor_scenario",
]
