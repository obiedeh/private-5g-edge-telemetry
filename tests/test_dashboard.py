"""Tests for the executive-technical dashboard generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from private5g_pipeline.benchmarks import run_benchmarks
from private5g_pipeline.business_cases.manufacturing import (
    run_manufacturing_business_case,
)
from private5g_pipeline.business_cases.pharma import run_pharma_business_case
from private5g_pipeline.portal.dashboard import (
    build_operational_decision_summary,
    generate_dashboard,
)
from private5g_pipeline.scenarios.manufacturing import (
    run_manufacturing_agv_scenario,
)
from private5g_pipeline.scenarios.pharma import run_pharma_bioreactor_scenario


@pytest.fixture(scope="module")
def evidence_root(tmp_path_factory):
    """Build a full reports/ tree the dashboard can render against."""
    root = tmp_path_factory.mktemp("dashboard_evidence")

    mfg_scenario = root / "scenarios" / "manufacturing_agv"
    pha_scenario = root / "scenarios" / "pharma_bioreactor"
    business_cases = root / "business_cases"

    run_manufacturing_agv_scenario(output_dir=mfg_scenario, seed=42)
    run_pharma_bioreactor_scenario(output_dir=pha_scenario, seed=42)
    run_manufacturing_business_case(
        output_dir=business_cases,
        canonical_pack_path=mfg_scenario / "scenario_metrics.json",
    )
    run_pharma_business_case(
        output_dir=business_cases,
        canonical_pack_path=pha_scenario / "scenario_metrics.json",
    )
    run_benchmarks(output_dir=root)

    return root


@pytest.fixture(scope="module")
def dashboard_html(evidence_root):
    output = evidence_root / "dashboard.html"
    html = generate_dashboard(
        output_path=output,
        manufacturing_metrics_path=str(
            evidence_root / "scenarios" / "manufacturing_agv" / "scenario_metrics.json"
        ),
        pharma_metrics_path=str(
            evidence_root / "scenarios" / "pharma_bioreactor" / "scenario_metrics.json"
        ),
        manufacturing_sensitivity_path=str(
            evidence_root / "business_cases" / "manufacturing_agv_sensitivity.json"
        ),
        pharma_sensitivity_path=str(
            evidence_root / "business_cases" / "pharma_bioreactor_sensitivity.json"
        ),
        benchmarks_path=str(evidence_root / "benchmarks.json"),
    )
    return output, html


def test_dashboard_file_exists_and_is_html(dashboard_html):
    path, html = dashboard_html
    assert Path(path).exists()
    assert html.startswith("<!doctype html>")
    assert "</html>" in html


def test_dashboard_carries_both_buyer_answers(dashboard_html):
    _, html = dashboard_html
    # Manufacturing headline.
    assert "100 AGVs" in html
    assert "20 ms" in html
    # Pharma cameo headline.
    assert "5 min" in html
    assert "1.00" in html


def test_dashboard_embeds_all_six_figures(dashboard_html):
    _, html = dashboard_html
    expected_figures = [
        "scenarios/manufacturing_agv/figures/01_latency_vs_fleet.png",
        "scenarios/manufacturing_agv/figures/02_edge_load_by_zone.png",
        "scenarios/manufacturing_agv/figures/03_budget_violation_timeline.png",
        "scenarios/pharma_bioreactor/figures/01_signal_timeline.png",
        "scenarios/pharma_bioreactor/figures/02_detector_zscore.png",
        "scenarios/pharma_bioreactor/figures/03_threshold_sweep.png",
    ]
    for figure in expected_figures:
        assert figure in html, f"expected dashboard to embed {figure}"


def test_dashboard_includes_per_fleet_and_threshold_tables(dashboard_html):
    _, html = dashboard_html
    # Manufacturing per-fleet table: should mention all fleet sizes.
    for fleet in (20, 40, 60, 80, 100, 120, 140, 160):
        assert str(fleet) in html
    # Pharma threshold sweep: each threshold value should appear.
    for threshold in ("2.0", "2.5", "3.0", "3.5", "4.0"):
        assert threshold in html


def test_dashboard_includes_benchmarks_when_available(dashboard_html):
    _, html = dashboard_html
    # Benchmark headline numbers.
    assert "rows / sec" in html
    assert "byte-identical" in html or "MISMATCH" in html


def test_dashboard_links_back_to_portal_and_brief(dashboard_html):
    _, html = dashboard_html
    assert 'href="index.html"' in html
    assert "../TECH_BRIEF.md" in html
    assert "business_cases/manufacturing_agv_capacity.md" in html
    assert "business_cases/pharma_bioreactor_anomaly.md" in html


def test_dashboard_includes_boundary_block(dashboard_html):
    _, html = dashboard_html
    assert "What I tested, what I didn't" in html
    assert "No live private 5G network" in html
    assert "No vendor RAN integration" in html
    assert "No MES/SCADA/PLC connector" in html
    assert "No production deployment claim" in html
    assert "seeded simulation" in html


def test_dashboard_includes_operator_console_sections(dashboard_html):
    _, html = dashboard_html
    assert "Decision" in html
    assert "Failure point" in html
    assert "Assembly edge GPU" in html
    assert "Seeded evidence; no live private 5G network." in html
    assert "Problem" in html
    assert "What I Built" in html
    assert "What I Found" in html
    assert "What I Would Do" in html
    assert "Operational Decision Summary" in html
    assert "Bottleneck Attribution" in html
    assert "Operator Action Plan" in html
    assert "Recommended simulated fleet ceiling" in html
    assert "First tested unsafe expansion" in html
    assert "18.39" in html
    assert "23.40" in html
    assert "Evidence demonstrated" in html
    assert "Boundary preserved" in html
    assert "Operator Console Readiness" in html


def test_dashboard_decision_artifacts_are_derived_from_metrics(evidence_root, dashboard_html):
    output, _ = dashboard_html
    metrics = json.loads(
        (evidence_root / "scenarios" / "manufacturing_agv" / "scenario_metrics.json").read_text()
    )
    sensitivity = json.loads(
        (evidence_root / "business_cases" / "manufacturing_agv_sensitivity.json").read_text()
    )
    decision = json.loads((Path(output).parent / "operational_decision_summary.json").read_text())
    expected = build_operational_decision_summary(metrics, sensitivity)

    assert decision["recommended_fleet_ceiling_agvs"] == metrics["max_fleet_under_budget"]
    assert decision["first_tested_unsafe_expansion_point_agvs"] == next(
        row["fleet_size"] for row in metrics["summary"] if row["budget_violated"]
    )
    assert decision == expected


def test_dashboard_orders_manufacturing_before_pharma(dashboard_html):
    _, html = dashboard_html
    assert html.index("<h2>Manufacturing</h2>") < html.index(
        "<h2>Secondary portability scenario</h2>"
    )
    assert "Secondary portability scenario, not the headline use case." in html


def test_dashboard_does_not_claim_forbidden_live_integrations(dashboard_html):
    _, html = dashboard_html
    html_without_boundaries = (
        html.replace("No MES/SCADA/PLC connector", "")
        .replace("MES/SCADA/PLC integration", "")
        .replace("No production deployment claim", "")
        .replace("Production deployment", "")
    )
    forbidden = [
        "live private 5G deployment",
        "NVIDIA Aerial integration",
        "MES integration",
        "SCADA integration",
        "PLC integration",
        "safety certified",
        "production-ready",
    ]
    for phrase in forbidden:
        assert phrase not in html_without_boundaries


def test_business_case_contains_decision_finding_recommendation_and_boundaries():
    text = Path("BUSINESS_CASE.md").read_text(encoding="utf-8")

    assert "Can a factory expand AGV fleet size" in text
    assert "stayed under budget through 100 AGVs" in text
    assert "At 120 AGVs, the 20 ms budget broke" in text
    assert "Cap expansion at 100 AGVs" in text
    assert "Seeded simulation only" in text
    assert "No live private 5G network" in text
