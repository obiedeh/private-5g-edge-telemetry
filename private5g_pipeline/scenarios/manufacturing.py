"""Manufacturing AGV-fleet vertical scenario.

Operational question:
    *Can the factory handle N more AGVs without violating the 20 ms vision
    control-loop latency budget?*

The scenario simulates one factory site with three URLLC cells covering an
assembly zone, a paint zone, and a warehouse zone. For each fleet size in
the sweep, it generates 1 hour of 5-minute-binned telemetry where:

* ``ue_count`` scales linearly with fleet size (each AGV is a UE attached
  to the URLLC slice),
* ``edge_inference_load`` rises with fleet size as the on-cell GPU pool
  saturates on per-AGV vision inference,
* ``latency_ms`` is a function of edge inference load — flat at the URLLC
  baseline until the GPU starts saturating, then climbs roughly linearly,
* ``drop_rate`` rises sharply once edge load exceeds the soft ceiling.

The output evidence pack contains the raw telemetry, the hourly KPIs, a
``scenario_metrics.json`` with the measured max-fleet-size that stays
under the latency budget, three plots, and a one-page
``dashboard_summary.md``.

This is a *pattern* — not a measurement of any real factory.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple, Sequence

import matplotlib

if matplotlib.get_backend().lower() in {"", "agg"} or not matplotlib.is_interactive():
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from private5g_pipeline.transform import (
    aggregate_hourly_per_cell_slice,
    engineer_features,
    qc_and_cast,
)

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = "reports/scenarios/manufacturing_agv"
DEFAULT_LATENCY_BUDGET_MS = 20.0
DEFAULT_FLEET_SIZES: tuple[int, ...] = (20, 40, 60, 80, 100, 120, 140, 160)
DEFAULT_SEED = 42


class _Cell(NamedTuple):
    cell_id: str
    zone: str
    band: int
    pci: int


# Three URLLC cells covering distinct factory zones.
_CELLS: tuple[_Cell, ...] = (
    _Cell("cell_mfg_001", "assembly",  78, 17),
    _Cell("cell_mfg_002", "paint",     78, 34),
    _Cell("cell_mfg_003", "warehouse", 78, 51),
)

_ZONE_WEIGHTS: dict[str, float] = {
    "assembly": 0.42,
    "paint":    0.34,
    "warehouse": 0.24,
}

# 1 hour at 5-minute bins → 12 samples per cell per fleet size.
_N_SAMPLES = 12
_BIN_MINUTES = 5

# Edge-AI load model parameters. Calibrated so the URLLC latency budget
# breaks between fleet=100 and fleet=120 in the default sweep — that's
# the operational story the scenario exists to tell.
_EDGE_LOAD_BASE = 0.20            # idle edge GPU utilisation
_EDGE_LOAD_PER_AGV = 0.010        # ΔGPU per additional AGV (per cell)
_EDGE_LOAD_NOISE = 0.025

# Latency model: flat until the GPU starts saturating, then linear ramp.
_LAT_BASELINE_MS = 6.0            # URLLC clean baseline
_LAT_SATURATION_THRESHOLD = 0.40  # edge load at which latency starts to rise
_LAT_SATURATION_GAIN = 50.0       # ms per unit of "over-budget" edge load
_LAT_NOISE_MS = 0.9

# Drop-rate model: sharp rise once the edge pipeline overflows.
_DROP_BASE = 0.005
_DROP_GAIN = 0.20
_DROP_KNEE = 0.85
_DROP_NOISE = 0.004


def _generate_fleet_telemetry(
    fleet_sizes: Sequence[int],
    seed: int,
) -> pd.DataFrame:
    """Generate raw schema-conformant telemetry across the fleet-size sweep."""
    rng = np.random.default_rng(seed)
    # Anchor timestamps to a fixed UTC date so committed artifacts are stable.
    start = datetime(2026, 1, 1, 6, 0, 0)

    rows: list[dict[str, object]] = []
    for sweep_idx, fleet_size in enumerate(fleet_sizes):
        sweep_start = start + timedelta(hours=sweep_idx)
        for cell in _CELLS:
            # Per-cell AGV share — assembly busiest, warehouse lightest.
            zone_weight = _ZONE_WEIGHTS[cell.zone]
            cell_fleet = fleet_size * zone_weight

            edge_load_expected = (
                _EDGE_LOAD_BASE + _EDGE_LOAD_PER_AGV * cell_fleet
            )

            for sample_idx in range(_N_SAMPLES):
                ts = sweep_start + timedelta(minutes=sample_idx * _BIN_MINUTES)
                edge_load = float(
                    np.clip(
                        edge_load_expected + rng.normal(0.0, _EDGE_LOAD_NOISE),
                        0.0,
                        1.0,
                    )
                )
                # Latency: flat until threshold, then linear in (load - threshold).
                lat_excess = max(0.0, edge_load - _LAT_SATURATION_THRESHOLD)
                latency = float(
                    max(
                        0.5,
                        _LAT_BASELINE_MS
                        + _LAT_SATURATION_GAIN * lat_excess
                        + rng.normal(0.0, _LAT_NOISE_MS),
                    )
                )
                drop_rate = float(
                    np.clip(
                        _DROP_BASE
                        + _DROP_GAIN * max(0.0, edge_load - _DROP_KNEE)
                        + rng.normal(0.0, _DROP_NOISE),
                        0.0,
                        1.0,
                    )
                )
                throughput = float(
                    max(0.5, rng.normal(55.0 + 0.35 * cell_fleet, 4.0))
                )
                rows.append(
                    {
                        "timestamp": ts,
                        "date": ts.date().isoformat(),
                        "cell_id": cell.cell_id,
                        "slice_type": "URLLC",
                        "prb_utilization_dl": float(
                            np.clip(rng.normal(0.30 + 0.0035 * cell_fleet, 0.04), 0, 1)
                        ),
                        "prb_utilization_ul": float(
                            np.clip(rng.normal(0.24 + 0.0030 * cell_fleet, 0.04), 0, 1)
                        ),
                        "sinr_db": float(rng.normal(19.0 - 0.025 * cell_fleet, 1.6)),
                        "rsrp_dbm": float(rng.normal(-87.0 - 0.020 * cell_fleet, 2.0)),
                        "latency_ms": latency,
                        "throughput_mbps": throughput,
                        "ue_count": int(max(1, round(cell_fleet))),
                        "qos_class_id": 7,
                        "edge_inference_load": edge_load,
                        "band": cell.band,
                        "arfcn": 632000,
                        "pci": cell.pci,
                        "handover_count": int(np.clip(rng.poisson(0.6 + 0.020 * cell_fleet), 0, 500)),
                        "drop_rate": drop_rate,
                        "ta": int(np.clip(rng.normal(18 + 0.06 * cell_fleet, 4), 0, 1000)),
                        "jitter_ms": float(np.clip(rng.normal(3.0 + 6.0 * edge_load, 0.9), 0, 500)),
                        "cell_state": "degraded" if drop_rate > 0.05 else "healthy",
                        "fleet_size": int(fleet_size),
                        "zone": cell.zone,
                    }
                )
    return pd.DataFrame.from_records(rows)


def _max_fleet_under_budget(
    summary: pd.DataFrame, budget_ms: float
) -> int | None:
    """Largest fleet size where p95 latency across all cells stays ≤ budget."""
    under = summary[summary["latency_ms_p95_worst_cell"] <= budget_ms]
    if under.empty:
        return None
    return int(under["fleet_size"].max())


def _fleet_summary(
    raw: pd.DataFrame, hourly: pd.DataFrame, budget_ms: float
) -> pd.DataFrame:
    """Per-fleet-size summary: worst-cell p95 latency, mean edge load, breach flag."""
    # Map curated hourly bins back to fleet_size via the raw frame's
    # (timestamp_hour, cell_id) → fleet_size index.
    raw = raw.copy()
    raw["hour"] = pd.to_datetime(raw["timestamp"]).dt.floor("h")
    fleet_lookup = (
        raw.groupby(["hour", "cell_id"])["fleet_size"].first().reset_index()
    )
    enriched = hourly.merge(fleet_lookup, on=["hour", "cell_id"], how="left")

    # Pure mean edge GPU load comes from the raw frame, not the
    # edge_latency_pressure column (which is edge × latency).
    edge_load_per_fleet = (
        raw.groupby("fleet_size")["edge_inference_load"].mean().reset_index(
            name="edge_inference_load_mean"
        )
    )

    grouped = enriched.groupby("fleet_size").agg(
        latency_ms_p95_worst_cell=("latency_ms_p95", "max"),
        latency_ms_p95_mean=("latency_ms_p95", "mean"),
        throughput_mbps_mean=("throughput_mbps_avg", "mean"),
        drop_rate_mean=("drop_rate_avg", "mean"),
    ).reset_index()
    grouped = grouped.merge(edge_load_per_fleet, on="fleet_size", how="left")
    grouped["budget_violated"] = grouped["latency_ms_p95_worst_cell"] > budget_ms
    return grouped


def _save(fig: plt.Figure, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _render_figures(
    summary: pd.DataFrame,
    raw: pd.DataFrame,
    budget_ms: float,
    fig_dir: Path,
) -> dict[str, str]:
    paths: dict[str, str] = {}

    # 1) Worst-cell p95 latency vs fleet size, with budget line.
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    colors = ["#2a6f97" if not v else "#c04a4a" for v in summary["budget_violated"]]
    ax.bar(
        summary["fleet_size"].astype(str),
        summary["latency_ms_p95_worst_cell"],
        color=colors,
        width=0.6,
    )
    ax.axhline(budget_ms, color="#444444", linestyle="--", linewidth=1.4, label=f"{budget_ms:.0f} ms budget")
    ax.set_title("AGV fleet capacity: worst-cell p95 latency vs fleet size")
    ax.set_xlabel("AGV fleet size")
    ax.set_ylabel("Worst-cell hourly p95 latency (ms)")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    paths["latency_vs_fleet"] = _save(fig, fig_dir / "01_latency_vs_fleet.png")

    # 2) Mean edge inference load vs fleet size, by zone.
    raw_by_zone = (
        raw.groupby(["fleet_size", "zone"])["edge_inference_load"].mean().reset_index()
    )
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    for zone, subset in raw_by_zone.groupby("zone"):
        ax.plot(
            subset["fleet_size"],
            subset["edge_inference_load"],
            marker="o",
            linewidth=1.8,
            label=zone,
        )
    ax.axhline(0.85, color="#c04a4a", linestyle="--", linewidth=1.2, label="0.85 saturation knee")
    ax.set_title("Edge GPU inference load vs fleet size, by factory zone")
    ax.set_xlabel("AGV fleet size")
    ax.set_ylabel("Mean edge inference load (0-1)")
    ax.legend(frameon=False, title="Zone")
    ax.grid(alpha=0.25)
    paths["edge_load_by_zone"] = _save(fig, fig_dir / "02_edge_load_by_zone.png")

    # 3) Budget-violation timeline: scatter latency vs timestamp coloured by violation.
    raw_sorted = raw.sort_values("timestamp").copy()
    raw_sorted["timestamp"] = pd.to_datetime(raw_sorted["timestamp"])
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    violating = raw_sorted["latency_ms"] > budget_ms
    ax.scatter(
        raw_sorted.loc[~violating, "timestamp"],
        raw_sorted.loc[~violating, "latency_ms"],
        s=10, alpha=0.5, color="#2a6f97", label="Within budget",
    )
    ax.scatter(
        raw_sorted.loc[violating, "timestamp"],
        raw_sorted.loc[violating, "latency_ms"],
        s=14, alpha=0.7, color="#c04a4a", label="Over budget",
    )
    ax.axhline(budget_ms, color="#444444", linestyle="--", linewidth=1.2)
    ax.set_title("Latency-budget violations over the fleet-size sweep")
    ax.set_xlabel("Time (each hour ≈ one fleet size step)")
    ax.set_ylabel("Sample latency (ms)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    paths["budget_timeline"] = _save(fig, fig_dir / "03_budget_violation_timeline.png")

    return paths


def _build_summary_md(
    summary: pd.DataFrame,
    max_fleet: int | None,
    budget_ms: float,
    figure_paths: dict[str, str],
    output_dir: Path,
) -> str:
    summary_rows = "\n".join(
        f"| {int(r.fleet_size)} | {r.latency_ms_p95_worst_cell:.2f} | "
        f"{r.latency_ms_p95_mean:.2f} | {r.edge_inference_load_mean:.2f} | "
        f"{r.drop_rate_mean*100:.2f} % | {'over' if r.budget_violated else 'ok'} |"
        for r in summary.itertuples(index=False)
    )

    headline = (
        f"{max_fleet} AGVs"
        if max_fleet is not None
        else "no fleet size in the sweep stays under budget"
    )

    def rel(p: str) -> str:
        try:
            return str(Path(p).resolve().relative_to(output_dir.resolve())).replace("\\", "/")
        except ValueError:
            return p

    lines = [
        "# Manufacturing — AGV fleet capacity over private 5G",
        "",
        "A factory floor running edge-AI vision on AGVs over private 5G. Ops wants to grow",
        "the fleet. The radio isn't the bottleneck — the edge GPU pool feeding inference to",
        f"the AGV cameras is. Add too many AGVs and vision latency slips past the {budget_ms:.0f} ms",
        "control-loop deadline. So: how many AGVs? The same deployment shape sits across the",
        "Industry 4.0 stack — NVIDIA-led AI compute, Ericsson and Nokia private wireless,",
        "Siemens and Rockwell on the automation side. The question is the same regardless of",
        "which vendors land in your specific deployment.",
        "",
        "## What we asked",
        "",
        f"Can the floor add more AGVs without breaking the {budget_ms:.0f} ms control-loop budget?",
        "",
        "## What we found",
        "",
        f"**{headline}.** That's the largest fleet where the worst cell's hourly p95 latency",
        f"stays at or below {budget_ms:.0f} ms. The assembly zone hits saturation first — it's",
        "the busiest zone, so its cell's GPU pool runs out of headroom before the others.",
        "Beyond that point latency climbs and drop rate starts to bite.",
        "",
        "## Per-fleet summary",
        "",
        "| Fleet size | Worst-cell p95 (ms) | Mean p95 (ms) | Mean edge load | Mean drop rate | Budget |",
        "|---:|---:|---:|---:|---:|:---|",
        summary_rows,
        "",
        "## Figures",
        "",
        f"![Latency vs fleet size]({rel(figure_paths['latency_vs_fleet'])})",
        "",
        f"![Edge load by zone]({rel(figure_paths['edge_load_by_zone'])})",
        "",
        f"![Budget-violation timeline]({rel(figure_paths['budget_timeline'])})",
        "",
        "## What we tested, what we didn't",
        "",
        "We tested:",
        "",
        "- One factory site, three URLLC cells (assembly, paint, warehouse).",
        "- AGV share by zone: assembly 42%, paint 34%, warehouse 24%.",
        f"- A GPU model where each AGV adds {_EDGE_LOAD_PER_AGV*100:.1f}% load to its cell, and",
        f"  latency is flat until edge load crosses {_LAT_SATURATION_THRESHOLD:.2f}, then rises at",
        f"  {_LAT_SATURATION_GAIN:.0f} ms per unit of over-budget load.",
        f"- A drop-rate model that picks up sharply once edge load passes {_DROP_KNEE:.2f}.",
        "",
        "We didn't test against real telemetry from any factory or vendor edge platform.",
        "Plugging in measured data would shift the coefficients above. The shape of the",
        "question — *there's a fleet size beyond which the budget breaks* — is what's portable.",
        "",
    ]
    return "\n".join(lines)


def run_manufacturing_agv_scenario(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    fleet_sizes: Sequence[int] = DEFAULT_FLEET_SIZES,
    latency_budget_ms: float = DEFAULT_LATENCY_BUDGET_MS,
    seed: int = DEFAULT_SEED,
) -> dict[str, object]:
    """Run the manufacturing AGV-fleet scenario and write the evidence pack."""
    out = Path(output_dir)
    fig_dir = out / "figures"
    out.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    raw = _generate_fleet_telemetry(fleet_sizes, seed)

    # Stash auxiliary cols (fleet_size, zone) — pipeline transforms don't know
    # about them. qc_and_cast accepts unknown extra columns and preserves them
    # only via the raw DataFrame; pull a clean view for the transform stack.
    raw_for_pipeline = raw.drop(columns=["fleet_size", "zone"], errors="ignore")
    clean = qc_and_cast(raw_for_pipeline)
    features = engineer_features(clean, carrier_bandwidth_mhz=100.0)
    hourly = aggregate_hourly_per_cell_slice(features)

    summary = _fleet_summary(raw, hourly, latency_budget_ms)
    max_fleet = _max_fleet_under_budget(summary, latency_budget_ms)

    figure_paths = _render_figures(summary, raw, latency_budget_ms, fig_dir)

    # Persist artifacts.
    raw_out = out / "telemetry.csv"
    raw.to_csv(raw_out, index=False)
    summary_out = out / "fleet_summary.csv"
    summary.to_csv(summary_out, index=False)
    hourly_out = out / "hourly_kpis.csv"
    hourly.to_csv(hourly_out, index=False)

    metrics = {
        "vertical": "manufacturing_agv",
        "question": (
            f"Can the factory handle N more AGVs without violating the "
            f"{latency_budget_ms:.0f} ms vision control-loop latency budget?"
        ),
        "latency_budget_ms": float(latency_budget_ms),
        "fleet_sweep": [int(f) for f in fleet_sizes],
        "max_fleet_under_budget": int(max_fleet) if max_fleet is not None else None,
        "n_cells": len(_CELLS),
        "samples_per_fleet_size_per_cell": _N_SAMPLES,
        "seed": int(seed),
        "summary": [
            {
                "fleet_size": int(r.fleet_size),
                "worst_cell_p95_latency_ms": round(float(r.latency_ms_p95_worst_cell), 3),
                "mean_p95_latency_ms": round(float(r.latency_ms_p95_mean), 3),
                "mean_edge_inference_load": round(float(r.edge_inference_load_mean), 3),
                "mean_drop_rate": round(float(r.drop_rate_mean), 5),
                "budget_violated": bool(r.budget_violated),
            }
            for r in summary.itertuples(index=False)
        ],
        "boundary": (
            "Planning estimate from a simulated GPU+latency profile. Not a "
            "measurement of any specific factory or vendor edge platform."
        ),
    }
    metrics_path = out / "scenario_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    md = _build_summary_md(summary, max_fleet, latency_budget_ms, figure_paths, out)
    (out / "dashboard_summary.md").write_text(md, encoding="utf-8")

    logger.info(
        "Manufacturing AGV scenario: max fleet under %.0f ms = %s",
        latency_budget_ms,
        max_fleet if max_fleet is not None else "n/a",
    )

    return {
        "raw": raw,
        "hourly": hourly,
        "summary": summary,
        "metrics": metrics,
        "figure_paths": figure_paths,
        "output_dir": str(out),
    }
