import numpy as np
import pandas as pd

from private5g_pipeline.transform import (
    aggregate_hourly_per_cell_slice,
    engineer_features,
    qc_and_cast,
)


def make_sample_df():
    rng = pd.date_range("2025-01-01T00:00:00", periods=12, freq="5min")
    rows = []
    for ts in rng:
        for slice_type in ["eMBB", "URLLC"]:
            rows.append(
                {
                    "timestamp": ts,
                    "date": ts.date().isoformat(),
                    "cell_id": "cell_test",
                    "slice_type": slice_type,
                    "prb_utilization_dl": 0.5 if slice_type == "eMBB" else 0.2,
                    "prb_utilization_ul": 0.3,
                    "latency_ms": 10 if slice_type == "eMBB" else 5,
                    "throughput_mbps": 50 if slice_type == "eMBB" else 10,
                    "ue_count": 10,
                }
            )
    return pd.DataFrame.from_records(rows)


def test_aggregate_hourly_per_cell_slice_basic():
    df = make_sample_df()
    df_clean = qc_and_cast(df)
    df_feat = engineer_features(df_clean, carrier_bandwidth_mhz=10.0)
    agg = aggregate_hourly_per_cell_slice(df_feat)

    assert len(agg) == 2

    expected_cols = {
        "date",
        "hour",
        "cell_id",
        "slice_type",
        "latency_ms_avg",
        "latency_ms_p95",
        "prb_util_dl_avg",
        "prb_util_ul_avg",
        "ue_count_peak",
    }
    assert expected_cols.issubset(set(agg.columns))

    embb_row = agg[agg["slice_type"] == "eMBB"].iloc[0]
    assert np.isclose(embb_row["prb_util_dl_avg"], 0.5)
    # ue_count_peak is the max across the 12 five-minute bins in the hour
    # (all bins have ue_count=10, so peak == 10)
    assert embb_row["ue_count_peak"] == 10
