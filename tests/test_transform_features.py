"""Unit tests for engineer_features() derived fields in transform.py."""
from __future__ import annotations

import pandas as pd
import pytest

from private5g_pipeline.transform import engineer_features, qc_and_cast


def _base_row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "timestamp": "2025-01-01T00:00:00",
        "cell_id": "c1",
        "slice_type": "eMBB",
        "prb_utilization_dl": 0.5,
        "prb_utilization_ul": 0.3,
        "latency_ms": 20.0,
        "throughput_mbps": 100.0,
        "edge_inference_load": 0.4,
    }
    base.update(overrides)
    return base


def _df(**overrides: object) -> pd.DataFrame:
    return qc_and_cast(pd.DataFrame([_base_row(**overrides)]))


# ---------------------------------------------------------------------------
# spectral_eff_bps_per_hz
# ---------------------------------------------------------------------------


def test_spectral_efficiency_computed():
    df = engineer_features(_df(), carrier_bandwidth_mhz=100.0)
    # 100 Mbps / 100 MHz = 1.0 bps/Hz
    assert pytest.approx(df.iloc[0]["spectral_eff_bps_per_hz"], rel=1e-6) == 1.0


def test_spectral_efficiency_custom_bandwidth():
    df = engineer_features(_df(throughput_mbps=50.0), carrier_bandwidth_mhz=50.0)
    assert pytest.approx(df.iloc[0]["spectral_eff_bps_per_hz"], rel=1e-6) == 1.0


# ---------------------------------------------------------------------------
# cell_load_class
# ---------------------------------------------------------------------------


def test_cell_load_class_low():
    df = engineer_features(_df(prb_utilization_dl=0.3))
    assert df.iloc[0]["cell_load_class"] == "low"


def test_cell_load_class_medium():
    df = engineer_features(_df(prb_utilization_dl=0.55))
    assert df.iloc[0]["cell_load_class"] == "medium"


def test_cell_load_class_high():
    df = engineer_features(_df(prb_utilization_dl=0.85))
    assert df.iloc[0]["cell_load_class"] == "high"


def test_cell_load_class_boundary_low_medium():
    """0.4 is the boundary — should be medium."""
    df = engineer_features(_df(prb_utilization_dl=0.4))
    assert df.iloc[0]["cell_load_class"] == "medium"


def test_cell_load_class_boundary_medium_high():
    """0.7 is the boundary — should be high."""
    df = engineer_features(_df(prb_utilization_dl=0.7))
    assert df.iloc[0]["cell_load_class"] == "high"


# ---------------------------------------------------------------------------
# is_congested
# ---------------------------------------------------------------------------


def test_is_congested_true_when_high_load_and_latency():
    df = engineer_features(_df(prb_utilization_dl=0.9, latency_ms=50.0))
    assert df.iloc[0]["is_congested"] == 1


def test_is_congested_false_low_load():
    df = engineer_features(_df(prb_utilization_dl=0.5, latency_ms=50.0))
    assert df.iloc[0]["is_congested"] == 0


def test_is_congested_false_low_latency():
    df = engineer_features(_df(prb_utilization_dl=0.9, latency_ms=10.0))
    assert df.iloc[0]["is_congested"] == 0


# ---------------------------------------------------------------------------
# edge_latency_pressure
# ---------------------------------------------------------------------------


def test_edge_latency_pressure_computed():
    df = engineer_features(_df(edge_inference_load=0.5, latency_ms=40.0))
    assert pytest.approx(df.iloc[0]["edge_latency_pressure"], rel=1e-6) == 0.5 * 40.0


def test_edge_latency_pressure_zero_when_no_load():
    df = engineer_features(_df(edge_inference_load=0.0, latency_ms=20.0))
    assert df.iloc[0]["edge_latency_pressure"] == 0.0


# ---------------------------------------------------------------------------
# ai_ran_efficiency_score
# ---------------------------------------------------------------------------


def test_ai_ran_efficiency_score_positive():
    df = engineer_features(_df(throughput_mbps=100.0, latency_ms=10.0, prb_utilization_dl=0.5))
    assert df.iloc[0]["ai_ran_efficiency_score"] > 0


def test_ai_ran_efficiency_score_decreases_with_higher_load():
    low = engineer_features(_df(prb_utilization_dl=0.2)).iloc[0]["ai_ran_efficiency_score"]
    high = engineer_features(_df(prb_utilization_dl=0.9)).iloc[0]["ai_ran_efficiency_score"]
    assert low > high


def test_ai_ran_efficiency_score_decreases_with_higher_latency():
    fast = engineer_features(_df(latency_ms=5.0)).iloc[0]["ai_ran_efficiency_score"]
    slow = engineer_features(_df(latency_ms=100.0)).iloc[0]["ai_ran_efficiency_score"]
    assert fast > slow


# ---------------------------------------------------------------------------
# Missing columns — features degrade gracefully
# ---------------------------------------------------------------------------


def test_engineer_features_no_throughput_skips_spectral_eff():
    row = {
        "timestamp": "2025-01-01T00:00:00",
        "cell_id": "c1",
        "slice_type": "eMBB",
        "prb_utilization_dl": 0.5,
        "latency_ms": 20.0,
    }
    df = qc_and_cast(pd.DataFrame([row]))
    out = engineer_features(df)
    assert "spectral_eff_bps_per_hz" not in out.columns


def test_engineer_features_no_edge_load_skips_pressure():
    row = {
        "timestamp": "2025-01-01T00:00:00",
        "cell_id": "c1",
        "slice_type": "eMBB",
        "latency_ms": 20.0,
        "throughput_mbps": 50.0,
        "prb_utilization_dl": 0.5,
    }
    df = qc_and_cast(pd.DataFrame([row]))
    out = engineer_features(df)
    assert "edge_latency_pressure" not in out.columns
