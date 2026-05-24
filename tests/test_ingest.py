"""Tests for private5g_pipeline.ingest."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from private5g_pipeline.ingest import generate_synthetic_ran_logs, ingest_csv_directory


# ---------------------------------------------------------------------------
# generate_synthetic_ran_logs
# ---------------------------------------------------------------------------


def test_synthetic_logs_deterministic():
    """Same seed must produce identical DataFrames."""
    df1 = generate_synthetic_ran_logs(n_cells=2, n_hours=1, seed=0)
    df2 = generate_synthetic_ran_logs(n_cells=2, n_hours=1, seed=0)
    pd.testing.assert_frame_equal(df1, df2)


def test_synthetic_logs_different_seeds():
    df1 = generate_synthetic_ran_logs(n_cells=2, n_hours=1, seed=1)
    df2 = generate_synthetic_ran_logs(n_cells=2, n_hours=1, seed=2)
    assert not df1["latency_ms"].equals(df2["latency_ms"])


def test_synthetic_logs_row_count():
    """n_cells × slices (3) × time-steps should equal total rows."""
    n_cells, n_hours, freq = 3, 2, "5min"
    df = generate_synthetic_ran_logs(n_cells=n_cells, n_hours=n_hours, freq=freq, seed=42)
    # 2 hours at 5-min bins → 24 steps per cell × 3 slices × 3 cells
    expected = n_cells * 3 * (n_hours * 60 // 5)
    assert len(df) == expected


def test_synthetic_logs_required_columns():
    df = generate_synthetic_ran_logs(n_cells=1, n_hours=1, seed=42)
    required = {"timestamp", "cell_id", "slice_type", "latency_ms", "throughput_mbps", "ue_count"}
    assert required.issubset(df.columns)


def test_synthetic_logs_timestamps_are_timezone_aware():
    """Timestamps must carry UTC timezone info, not be naive."""
    df = generate_synthetic_ran_logs(n_cells=1, n_hours=1, seed=42)
    assert df["timestamp"].dt.tz is not None, "timestamps should be tz-aware (UTC)"


def test_synthetic_logs_slice_types():
    df = generate_synthetic_ran_logs(n_cells=2, n_hours=1, seed=42)
    assert set(df["slice_type"].unique()) == {"eMBB", "URLLC", "mMTC"}


def test_synthetic_logs_numeric_ranges_sane():
    df = generate_synthetic_ran_logs(n_cells=3, n_hours=2, seed=42)
    assert df["prb_utilization_dl"].between(0, 1).all()
    assert df["prb_utilization_ul"].between(0, 1).all()
    assert (df["latency_ms"] >= 0).all()
    assert (df["throughput_mbps"] >= 0).all()


# ---------------------------------------------------------------------------
# ingest_csv_directory
# ---------------------------------------------------------------------------


def _write_csv(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_ingest_csv_directory_basic(tmp_path):
    _write_csv(
        tmp_path / "a.csv",
        "timestamp,cell_id,slice_type,latency_ms\n"
        "2025-01-01T00:00:00,c1,eMBB,10\n",
    )
    _write_csv(
        tmp_path / "b.csv",
        "timestamp,cell_id,slice_type,latency_ms\n"
        "2025-01-01T01:00:00,c2,URLLC,5\n",
    )
    df = ingest_csv_directory(tmp_path)
    assert len(df) == 2
    assert set(df["cell_id"]) == {"c1", "c2"}


def test_ingest_csv_directory_not_found():
    with pytest.raises(FileNotFoundError, match="does not exist"):
        ingest_csv_directory("/nonexistent/path/xyz")


def test_ingest_csv_directory_no_matching_files(tmp_path):
    (tmp_path / "readme.txt").write_text("hello")
    with pytest.raises(FileNotFoundError, match="No files matching"):
        ingest_csv_directory(tmp_path)


def test_ingest_csv_directory_legacy_suffix_pattern(tmp_path):
    """The old pattern='.csv' suffix form must still work."""
    _write_csv(
        tmp_path / "data.csv",
        "timestamp,cell_id\n2025-01-01T00:00:00,c1\n",
    )
    df = ingest_csv_directory(tmp_path, pattern=".csv")
    assert len(df) == 1


def test_ingest_csv_directory_skips_non_csv(tmp_path):
    _write_csv(
        tmp_path / "good.csv",
        "timestamp,cell_id\n2025-01-01T00:00:00,c1\n",
    )
    (tmp_path / "notes.txt").write_text("ignore me")
    df = ingest_csv_directory(tmp_path)
    assert len(df) == 1
