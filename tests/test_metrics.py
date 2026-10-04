"""Tests for private5g_pipeline.metrics."""
from __future__ import annotations

import pandas as pd

from private5g_pipeline.metrics import build_operator_summary, write_operator_summary
from private5g_pipeline.schema import SchemaValidationResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raw() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"cell_id": "c1", "slice_type": "eMBB"},
            {"cell_id": "c2", "slice_type": "URLLC"},
        ]
    )


def _curated() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "cell_id": "c1",
                "slice_type": "eMBB",
                "hour": pd.Timestamp("2025-01-01 00:00:00"),
                "congestion_ratio": 0.8,
                "latency_ms_p95": 45.0,
            },
            {
                "cell_id": "c2",
                "slice_type": "URLLC",
                "hour": pd.Timestamp("2025-01-01 01:00:00"),
                "congestion_ratio": 0.2,
                "latency_ms_p95": 12.0,
            },
        ]
    )


# ---------------------------------------------------------------------------
# build_operator_summary
# ---------------------------------------------------------------------------


def test_build_operator_summary_has_header():
    summary = build_operator_summary(_raw(), _curated())
    assert "# Private 5G Operator Summary" in summary


def test_build_operator_summary_row_counts():
    raw = _raw()
    curated = _curated()
    quarantined = pd.DataFrame([{"cell_id": "cx"}])
    summary = build_operator_summary(raw, curated, quarantined=quarantined)
    assert "Raw rows: 2" in summary
    assert "Curated rows: 2" in summary
    assert "Quarantined rows: 1" in summary


def test_build_operator_summary_with_schema_result():
    result = SchemaValidationResult(valid=False, errors=["missing col"], warnings=[])
    summary = build_operator_summary(_raw(), _curated(), schema_result=result)
    assert "Schema valid: False" in summary
    assert "Schema errors: 1" in summary


def test_build_operator_summary_top_congested_cells():
    summary = build_operator_summary(_raw(), _curated())
    assert "Top Congested Cells" in summary
    # c1 has higher congestion ratio, should appear first
    assert "c1" in summary


def test_build_operator_summary_worst_latency_slices():
    summary = build_operator_summary(_raw(), _curated())
    assert "Worst Latency Slices" in summary
    assert "45.00 ms" in summary


def test_build_operator_summary_no_congestion_data():
    curated = pd.DataFrame([{"cell_id": "c1"}])  # no congestion_ratio column
    summary = build_operator_summary(_raw(), curated)
    assert "No congestion data available" in summary


def test_build_operator_summary_no_latency_data():
    curated = pd.DataFrame([{"cell_id": "c1"}])  # no latency_ms_p95 column
    summary = build_operator_summary(_raw(), curated)
    assert "No latency data available" in summary


def test_build_operator_summary_top_n_respected():
    rows = [
        {"cell_id": f"c{i}", "slice_type": "eMBB",
         "hour": pd.Timestamp("2025-01-01"), "congestion_ratio": i * 0.1, "latency_ms_p95": float(i)}
        for i in range(10)
    ]
    curated = pd.DataFrame(rows)
    summary = build_operator_summary(_raw(), curated, top_n=2)
    # Only top 2 by congestion should appear in that section
    lines = [ln for ln in summary.splitlines() if ln.startswith("- c")]
    # Each section contributes top_n lines → 2 congestion + 2 latency = 4 total
    assert len(lines) == 4


# ---------------------------------------------------------------------------
# write_operator_summary
# ---------------------------------------------------------------------------


def test_write_operator_summary_creates_file(tmp_path):
    path = tmp_path / "summary.md"
    write_operator_summary("# Test Summary\n", str(path))
    assert path.exists()
    assert "# Test Summary" in path.read_text()


def test_write_operator_summary_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "nested" / "summary.md"
    write_operator_summary("content", str(path))
    assert path.exists()


# ---------------------------------------------------------------------------
# Re-export aliases from export module
# ---------------------------------------------------------------------------


def test_metrics_reexports_build_observability_report():
    from private5g_pipeline.metrics import build_observability_report
    report = build_observability_report(_raw(), _curated())
    assert "pipeline" in report


def test_metrics_reexports_write_report(tmp_path):
    from private5g_pipeline.metrics import write_report
    path = tmp_path / "r.json"
    write_report({"ok": True}, str(path))
    assert path.exists()
