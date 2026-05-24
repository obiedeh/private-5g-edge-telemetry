from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TelemetrySchema:
    """Column contract for private 5G RAN telemetry."""

    required_columns: frozenset[str] = frozenset(
        {
            "timestamp",
            "cell_id",
            "slice_type",
            "prb_utilization_dl",
            "prb_utilization_ul",
            "latency_ms",
            "throughput_mbps",
            "ue_count",
        }
    )
    numeric_ranges: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "prb_utilization_dl": (0.0, 1.0),
            "prb_utilization_ul": (0.0, 1.0),
            "sinr_db": (-30.0, 50.0),
            "rsrp_dbm": (-160.0, -40.0),
            "latency_ms": (0.0, 5000.0),
            "throughput_mbps": (0.0, 10000.0),
            "ue_count": (0.0, 100000.0),
            "edge_inference_load": (0.0, 1.0),
            "handover_count": (0.0, 500.0),
            "drop_rate": (0.0, 1.0),
            "ta": (0.0, 1000.0),
            "jitter_ms": (0.0, 500.0),
            "arfcn": (0.0, 1000000.0),
            "pci": (0.0, 503.0),
        }
    )
    slice_types: frozenset[str] = frozenset({"eMBB", "URLLC", "mMTC"})


DEFAULT_SCHEMA = TelemetrySchema()

# Backward-compat aliases
REQUIRED_COLUMNS: frozenset[str] = DEFAULT_SCHEMA.required_columns
NUMERIC_RANGES: dict[str, tuple[float, float]] = DEFAULT_SCHEMA.numeric_ranges


@dataclass(frozen=True)
class SchemaValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]


def validate_schema(
    df: pd.DataFrame,
    schema: TelemetrySchema = DEFAULT_SCHEMA,
) -> SchemaValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    missing = sorted(schema.required_columns.difference(df.columns))
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")

    if "timestamp" in df.columns:
        parsed = pd.to_datetime(df["timestamp"], errors="coerce", format="mixed")
        bad_count = int(parsed.isna().sum())
        if bad_count:
            errors.append(f"timestamp contains {bad_count} unparsable values")

    if "slice_type" in df.columns:
        unknown = sorted(set(df["slice_type"].dropna().astype(str)) - set(schema.slice_types))
        if unknown:
            warnings.append(f"slice_type contains unknown values: {', '.join(unknown)}")

    for col, (lower, upper) in schema.numeric_ranges.items():
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        bad_numeric = int(numeric.isna().sum())
        if bad_numeric:
            errors.append(f"{col} contains {bad_numeric} non-numeric values")
            continue
        out_of_range = int(((numeric < lower) | (numeric > upper)).sum())
        if out_of_range:
            warnings.append(
                f"{col} has {out_of_range} values outside expected range [{lower}, {upper}]"
            )

    return SchemaValidationResult(valid=not errors, errors=errors, warnings=warnings)


def quarantine_invalid_rows(
    df: pd.DataFrame,
    schema: TelemetrySchema = DEFAULT_SCHEMA,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split telemetry into valid rows and quarantined rows with rejection reasons.

    Vectorized: builds per-row rejection masks without Python-level iteration.
    """
    if df.empty:
        return df.copy(), df.copy()

    df = df.copy().reset_index(drop=True)
    n = len(df)

    # Per-row rejection reason accumulator (list of lists)
    reasons: list[list[str]] = [[] for _ in range(n)]

    missing_required = sorted(schema.required_columns.difference(df.columns))
    if missing_required:
        msg = f"missing required columns: {', '.join(missing_required)}"
        for r in reasons:
            r.append(msg)

    if "timestamp" in df.columns:
        bad_ts = pd.to_datetime(df["timestamp"], errors="coerce", format="mixed").isna()
        for i in np.flatnonzero(bad_ts.to_numpy()):
            reasons[i].append("invalid timestamp")

    for key in ("cell_id", "slice_type"):
        if key in df.columns:
            bad = df[key].isna() | (df[key].astype(str).str.strip() == "")
            for i in np.flatnonzero(bad.to_numpy()):
                reasons[i].append(f"missing {key}")

    for col, (lower, upper) in schema.numeric_ranges.items():
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        bad_numeric = numeric.isna()
        for i in np.flatnonzero(bad_numeric.to_numpy()):
            reasons[i].append(f"{col}: non-numeric")
        in_range = ~bad_numeric
        out_of_range = in_range & ((numeric < lower) | (numeric > upper))
        for i in np.flatnonzero(out_of_range.to_numpy()):
            reasons[i].append(f"{col}: out of range [{lower}, {upper}]")

    df["source_row_index"] = df.index
    is_rejected = [bool(r) for r in reasons]
    rejected_mask = pd.Series(is_rejected, index=df.index)

    valid_df = df[~rejected_mask].drop(columns=["source_row_index"], errors="ignore").copy()
    rejected_df = df[rejected_mask].copy()
    if not rejected_df.empty:
        rejected_df["quarantine_reasons"] = [
            "; ".join(dict.fromkeys(reasons[i]))
            for i in rejected_df.index
        ]

    return valid_df, rejected_df
