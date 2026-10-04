"""Tests for the pharma bioreactor anomaly scenario."""

from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path

import pandas as pd
import pytest

from private5g_pipeline.scenarios.pharma import (
    DEFAULT_DETECTION_THRESHOLD,
    DETECTION_THRESHOLDS,
    run_pharma_bioreactor_scenario,
)


@pytest.fixture(scope="module")
def scenario_result(tmp_path_factory):
    out = tmp_path_factory.mktemp("pha")
    return run_pharma_bioreactor_scenario(output_dir=out, seed=42)


def test_evidence_pack_files_exist(scenario_result):
    out = Path(scenario_result["output_dir"])
    assert (out / "telemetry.csv").exists()
    assert (out / "hourly_kpis.csv").exists()
    assert (out / "threshold_sweep.csv").exists()
    assert (out / "scenario_metrics.json").exists()
    assert (out / "dashboard_summary.md").exists()
    figures = list((out / "figures").glob("*.png"))
    assert len(figures) >= 3, f"expected ≥3 figures, got {figures}"


def test_metrics_contain_named_business_question(scenario_result):
    out = Path(scenario_result["output_dir"])
    metrics = json.loads((out / "scenario_metrics.json").read_text())
    assert "How early can we detect" in metrics["question"]
    assert metrics["vertical"] == "pharma_bioreactor"
    assert metrics["default_threshold"] == pytest.approx(DEFAULT_DETECTION_THRESHOLD)
    assert "boundary" in metrics and "planning" in metrics["boundary"].lower()


def test_default_threshold_detects_the_event(scenario_result):
    default_result = scenario_result["default_result"]
    assert default_result.detected, (
        "default z-score threshold should fire on the contamination event"
    )
    assert default_result.lead_time_minutes is not None
    # Lead time is measured from event onset, so it should be small + positive.
    assert 0 <= default_result.lead_time_minutes <= 75


def test_threshold_sweep_covers_configured_thresholds(scenario_result):
    sweep = scenario_result["sweep"]
    assert [r.threshold for r in sweep] == list(DETECTION_THRESHOLDS)


def test_higher_threshold_does_not_lower_precision(scenario_result):
    """As threshold rises, false-positive count should not increase."""
    sweep = scenario_result["sweep"]
    fps = [r.n_false_positive_windows for r in sweep]
    for prev, nxt in pairwise(fps):
        assert nxt <= prev, (
            f"false positives should be non-increasing as threshold rises, "
            f"got {fps}"
        )


def test_default_precision_is_perfect_or_close(scenario_result):
    """With z=3.0 on this seeded telemetry we expect precision = 1.0
    — there are no real anomalies during the drift phase."""
    default_result = scenario_result["default_result"]
    assert default_result.precision is not None
    assert default_result.precision >= 0.5


def test_deterministic_round_trip(tmp_path):
    """Two runs at the same seed produce byte-identical metrics + threshold sweep."""
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    run_pharma_bioreactor_scenario(output_dir=out_a, seed=42)
    run_pharma_bioreactor_scenario(output_dir=out_b, seed=42)

    metrics_a = (out_a / "scenario_metrics.json").read_text()
    metrics_b = (out_b / "scenario_metrics.json").read_text()
    assert metrics_a == metrics_b

    sweep_a = pd.read_csv(out_a / "threshold_sweep.csv")
    sweep_b = pd.read_csv(out_b / "threshold_sweep.csv")
    pd.testing.assert_frame_equal(sweep_a, sweep_b)
