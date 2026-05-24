from pathlib import Path

import pandas as pd

from private5g_pipeline.ingest import ingest_csv_directory
from private5g_pipeline.schema import validate_schema
from private5g_pipeline.transform import qc_and_cast


def test_bad_row_fixture_is_rejected_and_dropped():
    raw_dir = Path(__file__).resolve().parents[1] / "data" / "raw"
    df = ingest_csv_directory(str(raw_dir))

    schema_result = validate_schema(df)
    assert schema_result.valid is False
    assert schema_result.errors

    cleaned = qc_and_cast(df)
    assert "bad_cell" not in cleaned.get("cell_id", pd.Series(dtype=str)).tolist()
