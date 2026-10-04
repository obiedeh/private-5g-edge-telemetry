import shutil
from pathlib import Path

from private5g_pipeline.config import load_config
from private5g_pipeline.pipeline import run_pipeline_config


def test_fail_soft_pipeline_quarantines_bad_rows_and_writes_visuals(tmp_path):
    raw_source = Path(__file__).resolve().parents[1] / "data" / "raw"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for name in ["sample_cell_a.csv", "sample_cell_b.csv", "bad_row.csv"]:
        shutil.copy2(raw_source / name, raw_dir / name)

    config_path = tmp_path / "pipeline.yaml"
    output_path = tmp_path / "curated.parquet"
    quarantine_path = tmp_path / "quarantine.csv"
    visual_path = tmp_path / "visual.md"
    figure_dir = tmp_path / "figures"
    config_path.write_text(
        f"""
ingestion:
  mode: csv
  input_dir: {raw_dir}
transform:
  carrier_bandwidth_mhz: 100
  validate_schema: true
  fail_on_schema_error: false
export:
  output_parquet: {output_path}
  partition_cols: []
  metrics_report: null
  operator_summary_report: null
  quarantine_path: {quarantine_path}
  visual_report_path: {visual_path}
  visual_output_dir: {figure_dir}
streaming:
  enabled: false
""",
        encoding="utf-8",
    )

    result = run_pipeline_config(load_config(config_path))

    assert output_path.exists()
    assert quarantine_path.exists()
    assert visual_path.exists()
    assert figure_dir.exists()
    assert (figure_dir / "06_handover_latency.png").exists()
    assert len(list(figure_dir.glob("*.png"))) >= 4
    quarantine_text = quarantine_path.read_text(encoding="utf-8")
    assert "bad_cell" in quarantine_text
    assert "quarantine_reasons" in quarantine_text
    assert result["quarantined"].shape[0] == 1
    assert result["report"]["pipeline"]["quarantined_rows"] == 1
    assert result["report"]["pipeline"]["curated_rows"] > 0
