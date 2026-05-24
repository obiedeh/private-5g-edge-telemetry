from pathlib import Path
import shutil

import pandas as pd

from private5g_pipeline.pipeline import run_pipeline


def test_pipeline_ingest_csv(tmp_path):
    source_dir = Path(__file__).resolve().parents[1] / "data" / "raw"
    input_dir = tmp_path / "raw"
    input_dir.mkdir()
    for name in ["sample_cell_a.csv", "sample_cell_b.csv"]:
        shutil.copy2(source_dir / name, input_dir / name)
    out_parquet = tmp_path / "e2e.parquet"

    run_pipeline(
        input_dir=str(input_dir),
        output_parquet=str(out_parquet),
        generate_synthetic=False,
        partition_cols=None,
    )

    df = pd.read_parquet(str(out_parquet))
    assert len(df) > 0
    assert "cell_id" in df.columns
    assert "slice_type" in df.columns
