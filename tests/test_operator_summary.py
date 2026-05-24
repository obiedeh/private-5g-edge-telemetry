from private5g_pipeline.config import load_config
from private5g_pipeline.pipeline import run_pipeline_config


def test_operator_summary_contains_operational_sections(tmp_path):
    config_path = tmp_path / "pipeline.yaml"
    output_path = tmp_path / "hourly.parquet"
    summary_path = tmp_path / "summary.md"
    config_path.write_text(
        f"""
ingestion:
  mode: synthetic
  n_cells: 1
  n_hours: 1
  frequency: 5min
  seed: 11
transform:
  carrier_bandwidth_mhz: 100
  validate_schema: true
  fail_on_schema_error: true
export:
  output_parquet: {output_path}
  partition_cols: []
  metrics_report: null
  operator_summary_report: {summary_path}
  quarantine_path: null
  visual_report_path: null
streaming:
  enabled: false
""",
        encoding="utf-8",
    )

    run_pipeline_config(load_config(config_path))

    summary = summary_path.read_text(encoding="utf-8")
    assert "# Private 5G Operator Summary" in summary
    assert "Top Congested Cells" in summary
    assert "Worst Latency Slices" in summary
