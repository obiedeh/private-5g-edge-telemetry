"""Tests for the manufacturing AGV-fleet scenario."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from private5g_pipeline.scenarios.manufacturing import (
    DEFAULT_FLEET_SIZES,
    DEFAULT_LATENCY_BUDGET_MS,
    run_manufacturing_agv_scenario,
)


@pytest.fixture(scope="module")
def scenario_result(tmp_path_factory):
    out = tmp_path_factory.mktemp("mfg")
    return run_manufacturing_agv_scenario(output_dir=out, seed=42)


def test_evidence_pack_files_exist(scenario_result):
    out = Path(scenario_result["output_dir"])
    assert (out / "telemetry.csv").exists()
    assert (out / "hourly_kpis.csv").exists()
    assert (out / "fleet_summary.csv").exists()
    assert (out / "scenario_metrics.json").exists()
    assert (out / "dashboard_summary.md").exists()
    figures = list((out / "figures").glob("*.png"))
    assert len(figures) >= 3, f"expected ≥3 figures, got {figures}"


def test_metrics_contain_named_business_question(scenario_result):
    out = Path(scenario_result["output_dir"])
    metrics = json.loads((out / "scenario_metrics.json").read_text())
    assert "Can the factory handle N more AGVs" in metrics["question"]
    assert metrics["vertical"] == "manufacturing_agv"
    assert metrics["latency_budget_ms"] == pytest.approx(DEFAULT_LATENCY_BUDGET_MS)
    assert "boundary" in metrics and "planning" in metrics["boundary"].lower()


def test_summary_covers_full_sweep(scenario_result):
    summary = scenario_result["summary"]
    assert list(summary["fleet_size"]) == list(DEFAULT_FLEET_SIZES)


def test_latency_rises_with_fleet_size(scenario_result):
    """The smallest fleet must have lower worst-cell p95 than the largest."""
    summary = scenario_result["summary"]
    first = summary.iloc[0]["latency_ms_p95_worst_cell"]
    last = summary.iloc[-1]["latency_ms_p95_worst_cell"]
    assert last > first + 5.0, (
        f"expected latency to climb materially with fleet size, "
        f"got first={first:.2f} last={last:.2f}"
    )


def test_largest_fleet_violates_budget(scenario_result):
    """At the top of the sweep we expect a budget breach — that's the whole point."""
    summary = scenario_result["summary"]
    assert summary["budget_violated"].iloc[-1], (
        "largest fleet size should breach the latency budget; "
        "if not, the scenario parameters don't tell the operational story"
    )


def test_max_fleet_under_budget_is_in_sweep(scenario_result):
    metrics = scenario_result["metrics"]
    max_fleet = metrics["max_fleet_under_budget"]
    if max_fleet is not None:
        assert max_fleet in metrics["fleet_sweep"]


def test_deterministic_round_trip(tmp_path):
    """Two runs at the same seed produce byte-identical metrics + summary CSV."""
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    run_manufacturing_agv_scenario(output_dir=out_a, seed=42)
    run_manufacturing_agv_scenario(output_dir=out_b, seed=42)

    metrics_a = (out_a / "scenario_metrics.json").read_text()
    metrics_b = (out_b / "scenario_metrics.json").read_text()
    assert metrics_a == metrics_b

    summary_a = pd.read_csv(out_a / "fleet_summary.csv")
    summary_b = pd.read_csv(out_b / "fleet_summary.csv")
    pd.testing.assert_frame_equal(summary_a, summary_b)
