"""Tests for private5g_pipeline.export."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from private5g_pipeline.export import (
    build_markdown_report,
    build_observability_report,
    write_json_report,
    write_markdown_report,
    write_parquet,
    write_report,
)
from private5g_pipeline.schema import SchemaValidationResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"cell_id": "c1", "slice_type": "eMBB"},
            {"cell_id": "c2", "slice_type": "URLLC"},
        ]
    )


def _make_curated() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "cell_id": "c1",
                "slice_type": "eMBB",
                "latency_ms_p95": 25.0,
                "congestion_ratio": 0.4,
                "prb_util_dl_avg": 0.6,
                "throughput_mbps_avg": 80.0,
                "handover_count_avg": 1.2,
                "drop_rate_avg": 0.01,
                "jitter_ms_avg": 3.5,
                "edge_latency_pressure_avg": 5.0,
                "ai_ran_efficiency_score_avg": 12.0,
            }
        ]
    )


# ---------------------------------------------------------------------------
# build_observability_report
# ---------------------------------------------------------------------------


def test_build_observability_report_basic():
    report = build_observability_report(_make_raw(), _make_curated())
    assert report["pipeline"]["raw_rows"] == 2
    assert report["pipeline"]["curated_rows"] == 1
    assert report["pipeline"]["quarantined_rows"] == 0
    assert "eMBB" in report["pipeline"]["slices"]


def test_build_observability_report_with_schema_result():
    result = SchemaValidationResult(valid=True, errors=[], warnings=["w1"])
    report = build_observability_report(_make_raw(), _make_curated(), schema_result=result)
    assert report["schema"]["valid"] is True
    assert report["schema"]["warnings"] == ["w1"]


def test_build_observability_report_with_quarantine():
    quarantined = pd.DataFrame([{"cell_id": "cx", "slice_type": "eMBB"}])
    report = build_observability_report(_make_raw(), _make_curated(), quarantined=quarantined)
    assert report["pipeline"]["quarantined_rows"] == 1


def test_build_observability_report_observability_keys():
    report = build_observability_report(_make_raw(), _make_curated())
    obs = report["observability"]
    # latency_p95_max should be the max of the single row's value
    assert pytest.approx(obs["latency_ms_p95_max"], rel=1e-3) == 25.0
    assert "congestion_ratio_avg" in obs


# ---------------------------------------------------------------------------
# build_markdown_report
# ---------------------------------------------------------------------------


def test_build_markdown_report_contains_key_sections():
    report = build_observability_report(_make_raw(), _make_curated())
    md = build_markdown_report(report)
    assert "# Private 5G Telemetry Pipeline Report" in md
    assert "Pipeline Health" in md
    assert "Observability Signals" in md


def test_build_markdown_report_no_observability():
    report = build_observability_report(pd.DataFrame(), pd.DataFrame())
    md = build_markdown_report(report)
    assert "No observability metrics" in md


# ---------------------------------------------------------------------------
# write_json_report / write_report alias
# ---------------------------------------------------------------------------


def test_write_json_report_creates_valid_json(tmp_path):
    path = tmp_path / "report.json"
    write_json_report({"key": "value"}, path)
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["key"] == "value"


def test_write_report_alias_creates_file(tmp_path):
    path = tmp_path / "alias.json"
    write_report({"alias": True}, path)
    assert path.exists()


def test_write_json_report_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "nested" / "report.json"
    write_json_report({}, path)
    assert path.exists()


# ---------------------------------------------------------------------------
# write_markdown_report
# ---------------------------------------------------------------------------


def test_write_markdown_report_creates_file(tmp_path):
    path = tmp_path / "report.md"
    write_markdown_report("# Hello", path)
    assert path.read_text() == "# Hello"


def test_write_markdown_report_creates_parent_dirs(tmp_path):
    path = tmp_path / "sub" / "report.md"
    write_markdown_report("content", path)
    assert path.exists()


# ---------------------------------------------------------------------------
# write_parquet
# ---------------------------------------------------------------------------


def test_write_parquet_creates_file(tmp_path):
    df = pd.DataFrame([{"a": 1, "b": 2}])
    path = tmp_path / "out.parquet"
    write_parquet(df, path)
    assert path.exists()
    loaded = pd.read_parquet(path)
    assert list(loaded.columns) == ["a", "b"]


def test_write_parquet_creates_parent_dirs(tmp_path):
    df = pd.DataFrame([{"x": 1}])
    path = tmp_path / "deep" / "nested" / "out.parquet"
    write_parquet(df, path)
    assert path.exists()
