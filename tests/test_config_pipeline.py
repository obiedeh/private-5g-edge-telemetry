from private5g_pipeline.config import load_config
from private5g_pipeline.pipeline import run_pipeline_config


def test_config_driven_pipeline_writes_outputs(tmp_path):
    config_path = tmp_path / "pipeline.yaml"
    output_path = tmp_path / "hourly.parquet"
    report_path = tmp_path / "report.json"
    summary_path = tmp_path / "summary.md"
    visual_path = tmp_path / "visual.md"
    figure_dir = tmp_path / "figures"
    config_path.write_text(
        f"""
ingestion:
  mode: synthetic
  n_cells: 1
  n_hours: 1
  frequency: 5min
  seed: 7
transform:
  carrier_bandwidth_mhz: 50
  validate_schema: true
  fail_on_schema_error: true
export:
  output_parquet: {output_path}
  partition_cols: []
  metrics_report: {report_path}
  operator_summary_report: {summary_path}
  quarantine_path: {tmp_path / "quarantine.csv"}
  visual_report_path: {visual_path}
  visual_output_dir: {figure_dir}
streaming:
  enabled: true
  topic: private5g.ran.telemetry
  batch_size: 10
  output_events_path: {tmp_path / "events.ndjson"}
""",
        encoding="utf-8",
    )

    result = run_pipeline_config(load_config(config_path))

    assert output_path.exists()
    assert report_path.exists()
    assert summary_path.exists()
    assert visual_path.exists()
    assert figure_dir.exists()
    assert (tmp_path / "events.ndjson").exists()
    assert result["report"]["pipeline"]["raw_rows"] > 0
    assert result["report"]["schema"]["valid"] is True
