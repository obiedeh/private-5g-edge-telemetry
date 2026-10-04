"""Tests for private5g_pipeline.visuals."""
from __future__ import annotations

import pandas as pd

from private5g_pipeline.schema import SchemaValidationResult
from private5g_pipeline.visuals import build_visual_report, generate_visual_assets

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw() -> pd.DataFrame:
    ts = pd.date_range("2025-01-01", periods=12, freq="5min", tz="UTC")
    rows = []
    for t in ts:
        for sl in ["eMBB", "URLLC"]:
            rows.append(
                {
                    "timestamp": t,
                    "cell_id": "c1",
                    "slice_type": sl,
                    "latency_ms": 20.0 if sl == "eMBB" else 8.0,
                    "prb_utilization_dl": 0.6,
                    "throughput_mbps": 80.0,
                    "edge_inference_load": 0.4,
                }
            )
    return pd.DataFrame(rows)


def _make_curated() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "cell_id": "c1",
                "slice_type": sl,
                "hour": pd.Timestamp("2025-01-01 00:00", tz="UTC"),
                "latency_ms_avg": 20.0 if sl == "eMBB" else 8.0,
                "latency_ms_p95": 30.0 if sl == "eMBB" else 12.0,
                "throughput_mbps_avg": 80.0,
                "congestion_ratio": 0.3 if sl == "eMBB" else 0.1,
                "handover_count_avg": 1.5,
            }
            for sl in ["eMBB", "URLLC"]
        ]
    )


# ---------------------------------------------------------------------------
# generate_visual_assets
# ---------------------------------------------------------------------------


def test_generate_visual_assets_creates_data_flow_figure(tmp_path):
    paths = generate_visual_assets(
        raw=_make_raw(),
        curated=_make_curated(),
        quarantined=None,
        output_dir=str(tmp_path),
    )
    assert "data_flow" in paths
    assert (tmp_path / "01_data_flow.png").exists()


def test_generate_visual_assets_latency_pre_post(tmp_path):
    paths = generate_visual_assets(
        raw=_make_raw(),
        curated=_make_curated(),
        quarantined=None,
        output_dir=str(tmp_path),
    )
    assert "latency_pre_post" in paths
    assert (tmp_path / "02_latency_pre_post.png").exists()


def test_generate_visual_assets_congestion_rank(tmp_path):
    paths = generate_visual_assets(
        raw=_make_raw(),
        curated=_make_curated(),
        quarantined=None,
        output_dir=str(tmp_path),
    )
    assert "congestion_rank" in paths


def test_generate_visual_assets_with_quarantine(tmp_path):
    quarantined = pd.DataFrame([{"cell_id": "cx", "reason": "bad"}])
    paths = generate_visual_assets(
        raw=_make_raw(),
        curated=_make_curated(),
        quarantined=quarantined,
        output_dir=str(tmp_path),
    )
    assert "data_flow" in paths


def test_generate_visual_assets_empty_quarantine(tmp_path):
    paths = generate_visual_assets(
        raw=_make_raw(),
        curated=_make_curated(),
        quarantined=pd.DataFrame(),
        output_dir=str(tmp_path),
    )
    assert "data_flow" in paths


# ---------------------------------------------------------------------------
# build_visual_report
# ---------------------------------------------------------------------------


def test_build_visual_report_contains_header(tmp_path):
    figure_paths: dict[str, str] = {}
    report = build_visual_report(
        raw=_make_raw(),
        curated=_make_curated(),
        quarantined=None,
        schema_result=None,
        figure_paths=figure_paths,
        report_path=str(tmp_path / "report.md"),
    )
    assert "# Private 5G Visual Insights" in report


def test_build_visual_report_includes_schema_info(tmp_path):
    result = SchemaValidationResult(valid=True, errors=[], warnings=["w"])
    report = build_visual_report(
        raw=_make_raw(),
        curated=_make_curated(),
        quarantined=None,
        schema_result=result,
        figure_paths={},
        report_path=str(tmp_path / "r.md"),
    )
    assert "Schema valid: True" in report
    assert "Schema warnings: 1" in report


def test_build_visual_report_embeds_figure_links(tmp_path):
    # Create a dummy figure file so relpath resolves
    fig_path = tmp_path / "figures" / "01_data_flow.png"
    fig_path.parent.mkdir(parents=True)
    fig_path.write_bytes(b"")
    report = build_visual_report(
        raw=_make_raw(),
        curated=_make_curated(),
        quarantined=None,
        schema_result=None,
        figure_paths={"data_flow": str(fig_path)},
        report_path=str(tmp_path / "report.md"),
    )
    assert "data_flow" in report.lower() or "Data Flow" in report


def test_build_visual_report_operational_signal(tmp_path):
    report = build_visual_report(
        raw=_make_raw(),
        curated=_make_curated(),
        quarantined=None,
        schema_result=None,
        figure_paths={},
        report_path=str(tmp_path / "r.md"),
    )
    assert "Key Operational Signal" in report
    assert "congestion" in report.lower()
