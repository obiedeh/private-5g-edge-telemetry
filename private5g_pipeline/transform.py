from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from private5g_pipeline.schema import DEFAULT_SCHEMA

logger = logging.getLogger(__name__)

# Clip ranges mirror schema numeric_ranges so validated data is never silently clamped further.
_CLIP_RANGES: dict[str, tuple[float, float]] = {
    col: bounds
    for col, bounds in DEFAULT_SCHEMA.numeric_ranges.items()
    if col in {
        "prb_utilization_dl",
        "prb_utilization_ul",
        "sinr_db",
        "rsrp_dbm",
        "latency_ms",
        "throughput_mbps",
        "edge_inference_load",
        "drop_rate",
        "jitter_ms",
    }
}


def qc_and_cast(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize timestamps, drop invalid key rows, and clip telemetry to sane ranges."""
    df = df.copy()

    if "timestamp" not in df.columns:
        raise ValueError("Input telemetry is missing required column: timestamp")

    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", format="mixed")

    if "date" not in df.columns:
        df["date"] = df["timestamp"].dt.date.astype(str)

    before = len(df)
    df = df.dropna(subset=["timestamp", "cell_id", "slice_type"])
    logger.info("Dropped %d rows with invalid timestamp/cell_id/slice_type", before - len(df))

    for col, (lo, hi) in _CLIP_RANGES.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").clip(lo, hi)

    for col in ("ue_count", "handover_count", "ta", "band", "arfcn", "pci"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def engineer_features(df: pd.DataFrame, carrier_bandwidth_mhz: float = 100.0) -> pd.DataFrame:
    """Add telecom and AI-RAN observability features."""
    df = df.copy()
    bw_hz = carrier_bandwidth_mhz * 1e6

    if "throughput_mbps" in df.columns:
        df["spectral_eff_bps_per_hz"] = df["throughput_mbps"].astype(float) * 1e6 / bw_hz

    if "prb_utilization_dl" in df.columns:
        conditions = [
            df["prb_utilization_dl"] < 0.4,
            (df["prb_utilization_dl"] >= 0.4) & (df["prb_utilization_dl"] < 0.7),
            df["prb_utilization_dl"] >= 0.7,
        ]
        df["cell_load_class"] = np.select(conditions, ["low", "medium", "high"], default="unknown")

    if "prb_utilization_dl" in df.columns and "latency_ms" in df.columns:
        df["is_congested"] = (
            (df["prb_utilization_dl"] >= 0.8) & (df["latency_ms"] >= 30)
        ).astype(int)

    if {"edge_inference_load", "latency_ms"}.issubset(df.columns):
        df["edge_latency_pressure"] = (
            df["edge_inference_load"].astype(float) * df["latency_ms"].astype(float)
        )

    if {"throughput_mbps", "latency_ms", "prb_utilization_dl"}.issubset(df.columns):
        df["ai_ran_efficiency_score"] = (
            df["throughput_mbps"].astype(float)
            / (1.0 + df["latency_ms"].astype(float))
            * (1.0 - df["prb_utilization_dl"].astype(float).clip(0, 1) * 0.25)
        )

    return df


def aggregate_hourly_per_cell_slice(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw telemetry to hourly cell and slice observability KPIs."""
    df = df.copy()
    df["hour"] = df["timestamp"].dt.floor("h")
    group_cols = ["date", "hour", "cell_id", "slice_type"]

    def p95(x: pd.Series) -> float:
        values = x.dropna()
        return float(np.percentile(values, 95)) if len(values) else 0.0

    agg_spec = {
        "latency_ms": ["mean", p95],
        "prb_utilization_dl": "mean",
        "prb_utilization_ul": "mean",
        "sinr_db": "mean",
        "rsrp_dbm": "mean",
        "ue_count": "max",   # peak UEs attached in the hour; sum was 12× over-count
        "throughput_mbps": "mean",
        "handover_count": "mean",
        "drop_rate": "mean",
        "jitter_ms": "mean",
        "is_congested": "mean",
        "spectral_eff_bps_per_hz": "mean",
        "edge_latency_pressure": "mean",
        "ai_ran_efficiency_score": "mean",
    }
    agg_spec = {col: fn for col, fn in agg_spec.items() if col in df.columns}

    grouped = df.groupby(group_cols, dropna=False).agg(agg_spec)
    grouped.columns = [
        "_".join(c) if isinstance(c, tuple) else c for c in grouped.columns
    ]
    grouped = grouped.reset_index()
    grouped = grouped.rename(
        columns={
            "latency_ms_mean": "latency_ms_avg",
            "latency_ms_p95": "latency_ms_p95",
            "prb_utilization_dl_mean": "prb_util_dl_avg",
            "prb_utilization_ul_mean": "prb_util_ul_avg",
            "sinr_db_mean": "sinr_db_avg",
            "rsrp_dbm_mean": "rsrp_dbm_avg",
            "ue_count_max": "ue_count_peak",
            "throughput_mbps_mean": "throughput_mbps_avg",
            "handover_count_mean": "handover_count_avg",
            "drop_rate_mean": "drop_rate_avg",
            "jitter_ms_mean": "jitter_ms_avg",
            "is_congested_mean": "congestion_ratio",
            "spectral_eff_bps_per_hz_mean": "spectral_eff_bps_per_hz_avg",
            "edge_latency_pressure_mean": "edge_latency_pressure_avg",
            "ai_ran_efficiency_score_mean": "ai_ran_efficiency_score_avg",
        }
    )

    logger.info("Aggregated to hourly KPIs: %d rows", len(grouped))
    return grouped
