from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Iterable, Iterator

import pandas as pd


def telemetry_events(df: pd.DataFrame) -> Iterator[dict[str, object]]:
    """Yield row-level telemetry events in a Kafka-ready shape."""
    for record in df.to_dict(orient="records"):
        timestamp = record.get("timestamp")
        if hasattr(timestamp, "isoformat"):
            record["timestamp"] = timestamp.isoformat()
        yield {
            "key": str(record.get("cell_id", "")),
            "value": record,
            "headers": {
                "source": "private5g_pipeline",
                "domain": "ai-ran-telemetry",
            },
        }


def batched_events(
    events: Iterable[dict[str, object]],
    batch_size: int,
) -> Iterator[list[dict[str, object]]]:
    """Yield successive fixed-size batches from *events*.

    The final batch may be smaller than *batch_size*.
    """
    batch: list[dict[str, object]] = []
    for event in events:
        batch.append(event)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def write_event_log(
    events: Iterable[dict[str, object]],
    output_path: str,
    batch_size: int = 50,
) -> int:
    """Persist streaming events as newline-delimited JSON for local inspection.

    Events are written in batches of *batch_size* to bound peak memory use.
    Returns the total number of events written.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for batch in batched_events(events, batch_size):
            for event in batch:
                fh.write(json.dumps(event, sort_keys=True))
                fh.write("\n")
                count += 1
    return count
