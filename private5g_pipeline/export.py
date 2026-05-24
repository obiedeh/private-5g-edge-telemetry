from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from private5g_pipeline.schema import SchemaValidationResult

logger = logging.getLogger(__name__)


def write_parquet(
    df: pd.DataFrame,
    output_path: str | Path,
    partition_cols: list[str] | None = None,
    engine: str = "pyarrow",
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partitions = partition_cols or None
    logger.info("Writing Parquet to %s (partition_cols=%s)", output_path, partitions)
    df.to_parquet(path, engine=engine, index=False, partition_cols=partitions)


def build_observability_report(
    raw: pd.DataFrame,
    curated: pd.DataFrame,
    schema_result: SchemaValidationResult | None = None,
    quarantined: pd.DataFrame | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "positioning": {
            "scope": "simulation/data-first telecom telemetry infrastructure",
            "ai_native_use_cases": ["AI-RAN feature stores", "edge AI observability", "RAN KPI monitoring"],
            "live_network_claim": False,
        },
        "pipeline": {
            "raw_rows": int(len(raw)),
            "curated_rows": int(len(curated)),
            "quarantined_rows": int(len(quarantined)) if quarantined is not None else 0,
            "cells": int(raw["cell_id"].nunique()) if "cell_id" in raw else 0,
            "slices": sorted(raw["slice_type"].dropna().unique().tolist()) if "slice_type" in raw else [],
        },
        "schema": {
            "valid": schema_result.valid if schema_result else None,
            "errors": schema_result.errors if schema_result else [],
            "warnings": schema_result.warnings if schema_result else [],
        },
        "observability": {},
    }

    metric_map = {
        "latency_ms_p95": "latency_ms_p95_max",
        "congestion_ratio": "congestion_ratio_avg",
        "prb_util_dl_avg": "prb_util_dl_avg",
        "throughput_mbps_avg": "throughput_mbps_avg",
        "handover_count_avg": "handover_count_avg",
        "drop_rate_avg": "drop_rate_avg",
        "jitter_ms_avg": "jitter_ms_avg",
        "edge_latency_pressure_avg": "edge_latency_pressure_avg",
        "ai_ran_efficiency_score_avg": "ai_ran_efficiency_score_avg",
    }
    for source_col, output_key in metric_map.items():
        if source_col in curated.columns and len(curated):
            value = curated[source_col].max() if output_key.endswith("_max") else curated[source_col].mean()
            report["observability"][output_key] = float(value)

    return report


def write_report(report: dict[str, Any], output_path: str | Path) -> None:
    """Alias for :func:`write_json_report`; prefer that name in new code."""
    write_json_report(report, output_path)


def write_json_report(report: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def build_markdown_report(report: dict[str, Any]) -> str:
    pipeline = report["pipeline"]
    observability = report.get("observability", {})
    lines = [
        "# Private 5G Telemetry Pipeline Report",
        "",
        "Generated from simulated or file-based telemetry. Does not represent live 5G network integration.",
        "",
        "## Pipeline Health",
        "",
        f"- Raw rows: {pipeline['raw_rows']}",
        f"- Curated rows: {pipeline['curated_rows']}",
        f"- Quarantined rows: {pipeline['quarantined_rows']}",
        f"- Cells: {pipeline['cells']}",
        f"- Slices: {', '.join(pipeline['slices']) if pipeline['slices'] else 'none'}",
        "",
        "## Observability Signals",
        "",
    ]
    if observability:
        lines.extend(f"- {key}: {value:.4f}" for key, value in sorted(observability.items()))
    else:
        lines.append("- No observability metrics were produced.")
    lines.extend(
        [
            "",
            "## Engineering Positioning",
            "",
            "Simulation-first AI-native telecom telemetry infrastructure for AI-RAN, edge AI, and observability workflows.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(markdown: str, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
