from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from private5g_pipeline.config import PipelineConfig
from private5g_pipeline.export import (
    build_markdown_report,
    build_observability_report,
    write_json_report,
    write_markdown_report,
    write_parquet,
)
from private5g_pipeline.ingest import generate_synthetic_ran_logs, ingest_csv_directory
from private5g_pipeline.metrics import (
    build_operator_summary,
    write_operator_summary,
)
from private5g_pipeline.schema import SchemaValidationResult, quarantine_invalid_rows, validate_schema
from private5g_pipeline.streaming import telemetry_events, write_event_log
from private5g_pipeline.transform import (
    aggregate_hourly_per_cell_slice,
    engineer_features,
    qc_and_cast,
)
from private5g_pipeline.visuals import build_visual_report, generate_visual_assets

logger = logging.getLogger(__name__)


def _ingest(config: PipelineConfig) -> pd.DataFrame:
    ingestion = config.ingestion
    if ingestion.mode == "synthetic":
        return generate_synthetic_ran_logs(
            n_cells=ingestion.n_cells,
            n_hours=ingestion.n_hours,
            freq=ingestion.frequency,
            seed=ingestion.seed,
        )
    if ingestion.mode == "csv":
        if ingestion.input_dir is None:
            raise ValueError("ingestion.input_dir is required when ingestion.mode is csv")
        return ingest_csv_directory(ingestion.input_dir, pattern=ingestion.csv_suffix)
    raise ValueError(f"Unsupported ingestion mode: {ingestion.mode}")


def run_pipeline_config(config: PipelineConfig) -> dict[str, object]:
    raw = _ingest(config)
    working_raw = raw
    quarantined = pd.DataFrame()

    schema_result: SchemaValidationResult | None = None
    if config.transform.validate_schema:
        schema_result = validate_schema(raw)
        for warning in schema_result.warnings:
            logger.warning("Schema warning: %s", warning)
        if not schema_result.valid:
            valid_rows, quarantined = quarantine_invalid_rows(raw)
            if not quarantined.empty:
                logger.info("Quarantined %d invalid rows", len(quarantined))
                if config.export.quarantine_path:
                    Path(config.export.quarantine_path).parent.mkdir(parents=True, exist_ok=True)
                    quarantined.to_csv(config.export.quarantine_path, index=False)
            if config.transform.fail_on_schema_error:
                raise ValueError("; ".join(schema_result.errors))
            working_raw = valid_rows if not valid_rows.empty else raw.iloc[0:0].copy()

    clean = qc_and_cast(working_raw)
    features = engineer_features(
        clean,
        carrier_bandwidth_mhz=config.transform.carrier_bandwidth_mhz,
    )
    hourly = aggregate_hourly_per_cell_slice(features)

    if config.streaming.enabled:
        event_path = config.streaming.output_events_path
        event_count = write_event_log(
            telemetry_events(features),
            event_path,
            batch_size=config.streaming.batch_size,
        )
        logger.info(
            "Wrote %d events to %s (topic=%s)",
            event_count,
            event_path,
            config.streaming.topic,
        )

    write_parquet(
        hourly,
        config.export.output_parquet,
        partition_cols=config.export.partition_cols,
        engine=config.export.parquet_engine,
    )

    report = build_observability_report(raw, hourly, schema_result, quarantined)
    if config.export.metrics_report:
        write_json_report(report, config.export.metrics_report)
    if config.export.markdown_report:
        write_markdown_report(build_markdown_report(report), config.export.markdown_report)
    if config.export.operator_summary_report:
        summary = build_operator_summary(raw, hourly, schema_result, quarantined)
        write_operator_summary(summary, config.export.operator_summary_report)
    if config.export.visual_report_path:
        figure_paths = generate_visual_assets(
            raw=raw,
            curated=hourly,
            quarantined=quarantined,
            output_dir=config.export.visual_output_dir,
        )
        visual_report = build_visual_report(
            raw=raw,
            curated=hourly,
            quarantined=quarantined,
            schema_result=schema_result,
            figure_paths=figure_paths,
            report_path=config.export.visual_report_path,
        )
        Path(config.export.visual_report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(config.export.visual_report_path).write_text(visual_report, encoding="utf-8")

    return {
        "raw": raw,
        "features": features,
        "hourly": hourly,
        "quarantined": quarantined,
        "report": report,
    }


def run_pipeline(
    input_dir: str | None,
    output_parquet: str,
    generate_synthetic: bool = False,
    partition_cols: list[str] | None = None,
) -> None:
    """Backward-compatible script API used by existing tests and notebooks."""
    config = PipelineConfig()
    config.ingestion.mode = "synthetic" if generate_synthetic else "csv"
    config.ingestion.input_dir = input_dir
    config.export.output_parquet = output_parquet
    config.export.partition_cols = partition_cols or []
    config.export.metrics_report = None
    run_pipeline_config(config)
