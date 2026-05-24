from pathlib import Path

import pandas as pd

from private5g_pipeline.config import PipelineConfig
from private5g_pipeline.pipeline import run_pipeline_config


def test_pipeline_smoke_run_writes_outputs(tmp_path):
    output_parquet = tmp_path / "curated" / "hourly.parquet"
    metrics_report = tmp_path / "reports" / "observability.json"
    markdown_report = tmp_path / "reports" / "summary.md"

    config = PipelineConfig()
    config.ingestion.mode = "synthetic"
    config.ingestion.n_cells = 2
    config.ingestion.n_hours = 1
    config.export.output_parquet = str(output_parquet)
    config.export.metrics_report = str(metrics_report)
    config.export.markdown_report = str(markdown_report)
    config.export.operator_summary_report = None
    config.export.visual_report_path = None

    result = run_pipeline_config(config)

    assert Path(output_parquet).exists()
    assert Path(metrics_report).exists()
    assert Path(markdown_report).exists()
    assert not result["hourly"].empty
    assert not pd.read_parquet(output_parquet).empty
