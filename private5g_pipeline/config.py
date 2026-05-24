from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class IngestionConfig:
    mode: str = "synthetic"
    input_dir: str | None = None
    csv_suffix: str = ".csv"
    n_cells: int = 5
    n_hours: int = 24
    frequency: str = "5min"
    seed: int = 42


@dataclass
class TransformConfig:
    carrier_bandwidth_mhz: float = 100.0
    validate_schema: bool = True
    fail_on_schema_error: bool = True


@dataclass
class ExportConfig:
    output_parquet: str = "data/curated/private5g_ran_hourly.parquet"
    partition_cols: list[str] = field(default_factory=list)
    parquet_engine: str = "pyarrow"
    metrics_report: str | None = "data/reports/observability_report.json"
    markdown_report: str | None = None
    operator_summary_report: str | None = "data/reports/operator_summary.md"
    quarantine_path: str | None = "data/quarantine/rejected_rows.csv"
    visual_report_path: str | None = "data/reports/visual_insights.md"
    visual_output_dir: str = "data/reports/figures"


@dataclass
class StreamingConfig:
    enabled: bool = False
    topic: str = "private5g.ran.telemetry"
    batch_size: int = 50
    output_events_path: str = "data/events/private5g_events.ndjson"


@dataclass
class PipelineConfig:
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    transform: TransformConfig = field(default_factory=TransformConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{key}' must be a mapping.")
    return value


def _filter_kwargs(cls: type, values: dict[str, Any]) -> dict[str, Any]:
    known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
    return {k: v for k, v in values.items() if k in known}


def load_config(path: str | Path | None) -> PipelineConfig:
    if path is None:
        return PipelineConfig()

    with Path(path).open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise ValueError("Pipeline config must be a YAML mapping.")

    export_raw = _section(data, "export")
    # Legacy YAML configs used "operator_summary_report" where the dataclass now
    # calls the field "markdown_report".  Silently promote the old key so existing
    # config files keep working without modification.
    if "operator_summary_report" in export_raw and "markdown_report" not in export_raw:
        export_raw = {**export_raw, "markdown_report": export_raw["operator_summary_report"]}

    return PipelineConfig(
        ingestion=IngestionConfig(**_filter_kwargs(IngestionConfig, _section(data, "ingestion"))),
        transform=TransformConfig(**_filter_kwargs(TransformConfig, _section(data, "transform"))),
        export=ExportConfig(**_filter_kwargs(ExportConfig, export_raw)),
        streaming=StreamingConfig(**_filter_kwargs(StreamingConfig, _section(data, "streaming"))),
    )
