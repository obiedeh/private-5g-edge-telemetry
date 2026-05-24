import pandas as pd

from private5g_pipeline.schema import validate_schema
from private5g_pipeline.streaming import batched_events, telemetry_events, write_event_log


def test_validate_schema_reports_missing_required_columns():
    result = validate_schema(pd.DataFrame([{"timestamp": "2025-01-01T00:00:00"}]))

    assert result.valid is False
    assert result.errors


def test_streaming_events_are_kafka_ready_records():
    df = pd.DataFrame.from_records(
        [
            {
                "timestamp": pd.Timestamp("2025-01-01T00:00:00"),
                "cell_id": "cell_001",
                "slice_type": "URLLC",
            }
        ]
    )

    events = list(telemetry_events(df))
    batches = list(batched_events(events, batch_size=1))

    assert events[0]["key"] == "cell_001"
    assert events[0]["headers"]["domain"] == "ai-ran-telemetry"
    assert batches[0][0]["value"]["timestamp"] == "2025-01-01T00:00:00"


def test_write_event_log_creates_ndjson(tmp_path):
    df = pd.DataFrame.from_records(
        [
            {
                "timestamp": pd.Timestamp("2025-01-01T00:00:00"),
                "cell_id": "cell_002",
                "slice_type": "eMBB",
            }
        ]
    )

    events = list(telemetry_events(df))
    out_path = tmp_path / "events.ndjson"
    count = write_event_log(events, str(out_path))

    assert count == 1
    assert out_path.exists()
    assert "cell_002" in out_path.read_text(encoding="utf-8")
