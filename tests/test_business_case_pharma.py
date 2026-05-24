"""Tests for the pharma bioreactor anomaly business case."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from private5g_pipeline.business_cases.pharma import (
    run_pharma_business_case,
)
from private5g_pipeline.scenarios.pharma import (
    DETECTION_THRESHOLDS,
    run_pharma_bioreactor_scenario,
)


@pytest.fixture(scope="module")
def canonical_pack(tmp_path_factory):
    out = tmp_path_factory.mktemp("pha_scenario")
    run_pharma_bioreactor_scenario(output_dir=out, seed=42)
    return out / "scenario_metrics.json"


@pytest.fixture(scope="module")
def business_case_result(tmp_path_factory, canonical_pack):
    out = tmp_path_factory.mktemp("pha_business_case")
    return run_pharma_business_case(
        output_dir=out,
        canonical_pack_path=canonical_pack,
    )


def test_markdown_and_sensitivity_files_exist(business_case_result):
    md = Path(business_case_result["markdown_path"])
    js = Path(business_case_result["sensitivity_path"])
    assert md.exists()
    assert js.exists()
    assert md.name == "pharma_bioreactor_anomaly.md"
    assert js.name == "pharma_bioreactor_sensitivity.json"


def test_markdown_carries_question_answer_sensitivity_and_boundary(business_case_result):
    text = Path(business_case_result["markdown_path"]).read_text(encoding="utf-8")
    assert "## What we asked" in text
    assert "## What we found" in text
    assert "## Sensitivity" in text
    assert "## What we tested, what we didn't" in text
    # The canonical 5-minute lead time / precision-1.00 should appear.
    assert "5 min" in text
    assert "1.00" in text


def test_threshold_sensitivity_covers_configured_thresholds(business_case_result):
    js = json.loads(Path(business_case_result["sensitivity_path"]).read_text())
    thresholds = {row["threshold"] for row in js["threshold_sensitivity"]}
    assert thresholds == set(float(t) for t in DETECTION_THRESHOLDS)


def test_higher_threshold_does_not_increase_false_positives(business_case_result):
    js = json.loads(Path(business_case_result["sensitivity_path"]).read_text())
    rows = sorted(js["threshold_sensitivity"], key=lambda r: r["threshold"])
    fps = [r["fp_windows"] for r in rows]
    for prev, nxt in zip(fps, fps[1:]):
        assert nxt <= prev, (
            f"false positives should be non-increasing as threshold rises, got {fps}"
        )


def test_seed_sensitivity_includes_default_and_alternates(business_case_result):
    js = json.loads(Path(business_case_result["sensitivity_path"]).read_text())
    seeds = {row["seed"] for row in js["seed_sensitivity"]}
    assert 42 in seeds
    assert len(seeds) >= 3


def test_default_seed_remains_detected(business_case_result):
    """The default-seed run inside the business case must still detect the event."""
    js = json.loads(Path(business_case_result["sensitivity_path"]).read_text())
    default_row = next(r for r in js["seed_sensitivity"] if r["seed"] == 42)
    assert default_row["detected"] is True
    assert default_row["lead_time_minutes"] is not None
