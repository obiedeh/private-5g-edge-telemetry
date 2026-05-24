import pandas as pd

from private5g_pipeline.schema import validate_schema


def test_schema_validation_accepts_sample_shape():
    df = pd.DataFrame(
        [
            {
                "timestamp": "2026-05-14T00:00:00",
                "cell_id": "cell_001",
                "slice_type": "eMBB",
                "prb_utilization_dl": 0.5,
                "prb_utilization_ul": 0.4,
                "latency_ms": 20.0,
                "throughput_mbps": 100.0,
                "ue_count": 25,
            }
        ]
    )

    result = validate_schema(df)

    assert result.valid
    assert result.errors == []


def test_schema_validation_rejects_missing_required_column():
    df = pd.DataFrame([{"timestamp": "2026-05-14T00:00:00", "cell_id": "cell_001"}])

    result = validate_schema(df)

    assert not result.valid
    assert "Missing required columns" in result.errors[0]
