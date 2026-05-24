import pandas as pd

from private5g_pipeline.transform import qc_and_cast


def test_qc_and_cast_parses_timestamp_and_drops_bad_rows():
    rows = [
        {"timestamp": "2025-01-01T00:00:00", "cell_id": "c1", "slice_type": "eMBB", "prb_utilization_dl": 0.5},
        {"timestamp": "bad", "cell_id": "c2", "slice_type": "eMBB", "prb_utilization_dl": 0.5},
        {"timestamp": None, "cell_id": "c3", "slice_type": "eMBB", "prb_utilization_dl": 0.5},
    ]
    df = pd.DataFrame.from_records(rows)
    out = qc_and_cast(df)
    assert len(out) == 1
    assert out.iloc[0]["cell_id"] == "c1"


def test_qc_and_cast_clips_metrics():
    rows = [
        {"timestamp": "2025-01-01T00:00:00", "cell_id": "c1", "slice_type": "eMBB", "prb_utilization_dl": 2.0, "latency_ms": -5},
    ]
    df = pd.DataFrame.from_records(rows)
    out = qc_and_cast(df)
    assert out.iloc[0]["prb_utilization_dl"] == 1.0
    assert out.iloc[0]["latency_ms"] == 0.0
