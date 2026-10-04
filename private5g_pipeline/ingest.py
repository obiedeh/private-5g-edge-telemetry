from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_SLICE_PROFILES = {
    "eMBB":  {"latency": 18.0, "throughput": 180.0, "qci": 9, "load": 1.00},
    "URLLC": {"latency":  6.0, "throughput":  55.0, "qci": 7, "load": 0.70},
    "mMTC":  {"latency": 28.0, "throughput":  12.0, "qci": 1, "load": 0.45},
}

_BANDS = [3, 7, 20, 28, 41, 78]


def generate_synthetic_ran_logs(
    n_cells: int = 5,
    n_hours: int = 24,
    freq: str = "5min",
    seed: int = 42,
) -> pd.DataFrame:
    """Generate deterministic private 5G RAN KPI telemetry for local development."""
    rng = np.random.default_rng(seed)
    # Anchor synthetic data to the current UTC hour; keep timezone so downstream
    # consumers can do tz-aware comparisons without silent offset errors.
    start_ts = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    end_ts = start_ts + timedelta(hours=n_hours)
    timestamps = pd.date_range(start=start_ts, end=end_ts - pd.Timedelta(freq), freq=freq, tz=UTC)

    records: list[dict[str, object]] = []
    for cell_idx in range(1, n_cells + 1):
        cell_id = f"cell_{cell_idx:03d}"
        band = _BANDS[(cell_idx - 1) % len(_BANDS)]
        busy_center = start_ts + timedelta(hours=n_hours / 2)  # tz-aware; same tz as start_ts

        for ts in timestamps:
            delta_hours = abs((ts - busy_center).total_seconds()) / 3600.0
            load_factor = float(np.exp(-0.5 * (delta_hours / 3.0) ** 2))

            for slice_type, profile in _SLICE_PROFILES.items():
                slice_load = load_factor * float(profile["load"])
                dl_util = float(np.clip(rng.normal(0.25 + 0.62 * slice_load, 0.06), 0, 1))
                ul_util = float(np.clip(rng.normal(0.18 + 0.48 * slice_load, 0.05), 0, 1))
                latency = float(
                    max(0.0, rng.normal(float(profile["latency"]) + 22.0 * slice_load, 2.5))
                )
                throughput = float(
                    max(0.0, rng.normal(float(profile["throughput"]) * (0.25 + slice_load), 16.0))
                )
                drop_rate = float(np.clip(rng.normal(0.006 + 0.045 * slice_load, 0.006), 0, 1))
                handovers = int(np.clip(rng.poisson(0.5 + 3.0 * slice_load), 0, 500))
                edge_load = float(np.clip(rng.normal(0.25 + 0.5 * slice_load, 0.1), 0, 1))

                records.append(
                    {
                        "timestamp": ts,
                        "date": ts.date().isoformat(),
                        "cell_id": cell_id,
                        "slice_type": slice_type,
                        "prb_utilization_dl": dl_util,
                        "prb_utilization_ul": ul_util,
                        "sinr_db": float(rng.normal(18 - 6 * slice_load, 2.5)),
                        "rsrp_dbm": float(rng.normal(-88 - 4 * slice_load, 3.5)),
                        "latency_ms": latency,
                        "throughput_mbps": throughput,
                        "ue_count": int(np.clip(rng.normal(20 + 85 * slice_load, 8), 1, 500)),
                        "qos_class_id": int(profile["qci"]),
                        "edge_inference_load": edge_load,
                        "band": band,
                        "arfcn": 360000 + cell_idx * 120,
                        "pci": (cell_idx * 17) % 503,
                        "handover_count": handovers,
                        "drop_rate": drop_rate,
                        "ta": int(np.clip(rng.normal(18 + 22 * slice_load, 5), 0, 1000)),
                        "jitter_ms": float(np.clip(rng.normal(4 + 12 * slice_load, 1.5), 0, 500)),
                        "cell_state": "degraded" if drop_rate > 0.05 or handovers > 6 else "healthy",
                    }
                )

    df = pd.DataFrame.from_records(records)
    logger.info("Generated synthetic RAN logs: %d rows", len(df))
    return df


def ingest_csv_directory(input_dir: str | Path, pattern: str = "*.csv") -> pd.DataFrame:
    """Read compatible telemetry CSV files from a directory.

    Args:
        input_dir: Directory to scan for CSV files.
        pattern: Glob pattern used to match files (default ``"*.csv"``).
            The legacy suffix form ``".csv"`` is accepted for backwards
            compatibility and normalised to ``"*.csv"`` automatically.
    """
    root = Path(input_dir)
    if not root.exists():
        raise FileNotFoundError(f"Input directory does not exist: {root}")

    # Accept the legacy suffix form (".csv") used by old configs/tests.
    glob_pattern = pattern if "*" in pattern else f"*{pattern}"
    csv_files = sorted(root.glob(glob_pattern))
    if not csv_files:
        raise FileNotFoundError(f"No files matching '{glob_pattern}' found in {root}")

    frames = [pd.read_csv(path) for path in csv_files]
    combined = pd.concat(frames, ignore_index=True)
    logger.info("Ingested %d rows from %d files", len(combined), len(csv_files))
    return combined
