"""Tests for the manufacturing AGV-capacity business case."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from private5g_pipeline.business_cases.manufacturing import (
    run_manufacturing_business_case,
)
from private5g_pipeline.scenarios.manufacturing import (
    run_manufacturing_agv_scenario,
)


@pytest.fixture(scope="module")
def canonical_pack(tmp_path_factory):
    """Generate a canonical scenario pack the business case can read from."""
    out = tmp_path_factory.mktemp("mfg_scenario")
    run_manufacturing_agv_scenario(output_dir=out, seed=42)
    return out / "scenario_metrics.json"


@pytest.fixture(scope="module")
def business_case_result(tmp_path_factory, canonical_pack):
    out = tmp_path_factory.mktemp("mfg_business_case")
    return run_manufacturing_business_case(
        output_dir=out,
        canonical_pack_path=canonical_pack,
    )


def test_markdown_and_sensitivity_files_exist(business_case_result):
    md = Path(business_case_result["markdown_path"])
    js = Path(business_case_result["sensitivity_path"])
    assert md.exists()
    assert js.exists()
    assert md.name == "manufacturing_agv_capacity.md"
    assert js.name == "manufacturing_agv_sensitivity.json"


def test_markdown_carries_question_answer_sensitivity_and_boundary(business_case_result):
    text = Path(business_case_result["markdown_path"]).read_text(encoding="utf-8")
    # One question, one answer, sensitivity, scope disclosure.
    assert "## What we asked" in text
    assert "## What we found" in text
    assert "## Sensitivity" in text
    assert "## What we tested, what we didn't" in text
    # The canonical max-fleet value must appear in the answer paragraph.
    assert "100 AGVs" in text


def test_sensitivity_json_has_three_sections(business_case_result):
    js = json.loads(Path(business_case_result["sensitivity_path"]).read_text())
    assert set(js.keys()) >= {
        "budget_sensitivity",
        "fine_grained_fleet_search",
        "seed_sensitivity",
    }


def test_budget_sensitivity_is_monotonic(business_case_result):
    """Tighter budget → smaller or equal max fleet."""
    js = json.loads(Path(business_case_result["sensitivity_path"]).read_text())
    rows = sorted(js["budget_sensitivity"], key=lambda r: r["latency_budget_ms"])
    max_fleets = [r["max_fleet_under_budget"] for r in rows]
    # None values are allowed (e.g. tightest budget breaks at fleet=20).
    numeric = [v for v in max_fleets if v is not None]
    assert numeric == sorted(numeric), (
        f"expected monotonic non-decreasing max fleet with looser budget, got {max_fleets}"
    )


def test_fine_grained_search_has_a_crossing_point(business_case_result):
    """The fine-grained search should contain at least one ok and one over row."""
    js = json.loads(Path(business_case_result["sensitivity_path"]).read_text())
    rows = js["fine_grained_fleet_search"]
    violations = [r["budget_violated"] for r in rows]
    assert any(v is True for v in violations) and any(v is False for v in violations), (
        f"fine-grained search should bracket the budget crossing; got {violations}"
    )


def test_seed_sensitivity_includes_default_and_alternates(business_case_result):
    js = json.loads(Path(business_case_result["sensitivity_path"]).read_text())
    seeds = {r["seed"] for r in js["seed_sensitivity"]}
    assert 42 in seeds
    assert len(seeds) >= 3
