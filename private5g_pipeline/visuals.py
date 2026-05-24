from __future__ import annotations

import os
from pathlib import Path

import matplotlib

# Switch to the non-interactive Agg backend only when no display is configured.
# Guarding the call prevents clobbering an interactive backend (e.g. TkAgg)
# when this module is imported in a notebook or interactive session.
if matplotlib.get_backend().lower() in {"", "agg"} or not matplotlib.is_interactive():
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from private5g_pipeline.schema import SchemaValidationResult


def _save(fig: plt.Figure, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def generate_visual_assets(
    raw: pd.DataFrame,
    curated: pd.DataFrame,
    quarantined: pd.DataFrame | None,
    output_dir: str,
) -> dict[str, str]:
    """Render compact publishable figures from raw and curated telemetry."""
    root = Path(output_dir)
    paths: dict[str, str] = {}

    quarantine_rows = len(quarantined) if quarantined is not None else 0

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.bar(
        ["Raw", "Quarantined", "Curated"],
        [len(raw), quarantine_rows, len(curated)],
        color=["#7b8d93", "#c04a4a", "#2a6f97"],
        width=0.62,
    )
    ax.set_title("Telemetry Flow: Raw to Curated")
    ax.set_ylabel("Rows")
    ax.grid(axis="y", alpha=0.2)
    paths["data_flow"] = _save(fig, root / "01_data_flow.png")

    if "latency_ms" in raw.columns and "latency_ms_p95" in curated.columns:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        slice_order = [s for s in ["eMBB", "URLLC", "mMTC"] if s in raw["slice_type"].dropna().unique()]
        if not slice_order:
            slice_order = sorted(raw["slice_type"].dropna().unique().tolist())

        data = [
            pd.to_numeric(raw.loc[raw["slice_type"] == s, "latency_ms"], errors="coerce").dropna()
            for s in slice_order
        ]
        axes[0].boxplot(data, tick_labels=slice_order, patch_artist=True, showfliers=False)
        axes[0].set_title("Pre: Raw Latency Distribution")
        axes[0].set_ylabel("Latency (ms)")
        axes[0].grid(axis="y", alpha=0.2)

        post = curated.groupby("slice_type")["latency_ms_p95"].mean().reindex(slice_order)
        axes[1].bar(post.index.astype(str), post.values, color="#2a6f97")
        axes[1].set_title("Post: Hourly Latency p95 by Slice")
        axes[1].set_ylabel("Latency p95 (ms)")
        axes[1].grid(axis="y", alpha=0.2)
        paths["latency_pre_post"] = _save(fig, root / "02_latency_pre_post.png")

    if "congestion_ratio" in curated.columns and len(curated):
        top = curated.sort_values("congestion_ratio", ascending=False).head(5)
        fig, ax = plt.subplots(figsize=(8.5, 4.75))
        labels = [f"{row.cell_id}\n{row.slice_type}" for row in top.itertuples(index=False)]
        ax.barh(labels[::-1], top["congestion_ratio"].iloc[::-1], color="#c04a4a")
        ax.set_title("Top Congested Cell/Slice Combinations")
        ax.set_xlabel("Congestion ratio")
        ax.grid(axis="x", alpha=0.2)
        paths["congestion_rank"] = _save(fig, root / "03_congestion_rank.png")

    if "latency_ms_avg" in curated.columns and len(curated):
        candidate = curated.sort_values("latency_ms_p95", ascending=False).iloc[0]
        raw_match = raw[
            (raw["cell_id"] == candidate["cell_id"]) & (raw["slice_type"] == candidate["slice_type"])
        ].copy()
        if not raw_match.empty:
            raw_match["timestamp"] = pd.to_datetime(
                raw_match["timestamp"], errors="coerce", format="mixed"
            )
            raw_match = raw_match.dropna(subset=["timestamp"])
            fig, ax = plt.subplots(figsize=(10, 4.75))
            ax.scatter(
                raw_match["timestamp"],
                pd.to_numeric(raw_match["latency_ms"], errors="coerce"),
                s=18,
                alpha=0.55,
                color="#7b8d93",
                label="Raw samples",
            )
            trend = curated[
                (curated["cell_id"] == candidate["cell_id"]) & (curated["slice_type"] == candidate["slice_type"])
            ].sort_values("hour")
            ax.plot(
                trend["hour"],
                trend["latency_ms_avg"],
                color="#2a6f97",
                linewidth=2.2,
                marker="o",
                label="Curated hourly mean",
            )
            ax.set_title(
                f"Pre/Post Latency Trend: {candidate['cell_id']} / {candidate['slice_type']}"
            )
            ax.set_ylabel("Latency (ms)")
            ax.grid(alpha=0.2)
            ax.legend(frameon=False)
            paths["latency_trend"] = _save(fig, root / "04_latency_trend.png")

    if {"throughput_mbps_avg", "latency_ms_avg"}.issubset(curated.columns) and len(curated):
        fig, ax = plt.subplots(figsize=(9.5, 5.5))
        for slice_type, subset in curated.groupby("slice_type"):
            ax.scatter(
                subset["throughput_mbps_avg"],
                subset["latency_ms_avg"],
                s=(subset["congestion_ratio"] * 260 + 30) if "congestion_ratio" in subset.columns else 55,
                alpha=0.78,
                label=str(slice_type),
            )
        ax.set_title("Throughput vs Latency by Slice")
        ax.set_xlabel("Hourly throughput mean (Mbps)")
        ax.set_ylabel("Hourly latency mean (ms)")
        ax.grid(alpha=0.2)
        ax.legend(frameon=False, title="Slice")
        paths["throughput_latency"] = _save(fig, root / "05_throughput_latency.png")

    if {"handover_count_avg", "latency_ms_avg"}.issubset(curated.columns) and len(curated):
        fig, ax = plt.subplots(figsize=(9.5, 5.5))
        for slice_type, subset in curated.groupby("slice_type"):
            ax.scatter(
                subset["handover_count_avg"],
                subset["latency_ms_avg"],
                s=70,
                alpha=0.8,
                label=str(slice_type),
            )
        ax.set_title("Handover Count vs Latency by Slice")
        ax.set_xlabel("Hourly handover count mean")
        ax.set_ylabel("Hourly latency mean (ms)")
        ax.grid(alpha=0.2)
        ax.legend(frameon=False, title="Slice")
        paths["handover_latency"] = _save(fig, root / "06_handover_latency.png")

    return paths


def build_visual_report(
    raw: pd.DataFrame,
    curated: pd.DataFrame,
    quarantined: pd.DataFrame | None,
    schema_result: SchemaValidationResult | None,
    figure_paths: dict[str, str],
    report_path: str,
) -> str:
    lines = [
        "# Private 5G Visual Insights",
        "",
        f"- Raw rows: {len(raw)}",
        f"- Curated rows: {len(curated)}",
        f"- Quarantined rows: {len(quarantined) if quarantined is not None else 0}",
    ]

    if schema_result is not None:
        lines.extend(
            [
                f"- Schema valid: {schema_result.valid}",
                f"- Schema errors: {len(schema_result.errors)}",
                f"- Schema warnings: {len(schema_result.warnings)}",
            ]
        )

    if "congestion_ratio" in curated.columns and len(curated):
        worst = curated.sort_values("congestion_ratio", ascending=False).iloc[0]
        lines.extend(
            [
                "",
                "## Key Operational Signal",
                f"- Most congested slice: {worst['cell_id']} / {worst['slice_type']}",
                f"- Congestion ratio: {float(worst['congestion_ratio']):.2f}",
                f"- Hourly latency p95: {float(worst.get('latency_ms_p95', 0.0)):.2f} ms",
            ]
        )

    lines.extend(["", "## Figures"])
    report_dir = Path(report_path).parent
    for key in [
        "data_flow",
        "latency_pre_post",
        "congestion_rank",
        "latency_trend",
        "throughput_latency",
        "handover_latency",
    ]:
        path = figure_paths.get(key)
        if path:
            rel = os.path.relpath(path, report_dir)
            lines.extend(["", f"### {key.replace('_', ' ').title()}", f"![{key}]({rel})"])

    return "\n".join(lines) + "\n"
