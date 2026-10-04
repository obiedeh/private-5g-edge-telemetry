from private5g_pipeline.ingest import generate_synthetic_ran_logs
from private5g_pipeline.transform import (
    aggregate_hourly_per_cell_slice,
    engineer_features,
    qc_and_cast,
)


def test_feature_generation_adds_ai_ran_and_edge_signals():
    raw = generate_synthetic_ran_logs(n_cells=1, n_hours=1, seed=7)
    clean = qc_and_cast(raw)

    featured = engineer_features(clean, carrier_bandwidth_mhz=100.0)

    assert "spectral_eff_bps_per_hz" in featured.columns
    assert "edge_latency_pressure" in featured.columns
    assert "ai_ran_efficiency_score" in featured.columns
    assert featured["cell_load_class"].isin(["low", "medium", "high"]).all()


def test_hourly_aggregation_outputs_cell_slice_rows():
    featured = engineer_features(qc_and_cast(generate_synthetic_ran_logs(n_cells=1, n_hours=1, seed=8)))

    hourly = aggregate_hourly_per_cell_slice(featured)

    assert {"hour", "cell_id", "slice_type", "latency_ms_avg", "throughput_mbps_avg"}.issubset(hourly.columns)
    assert len(hourly) == 3
