"""Tests for the evidence-portal generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from private5g_pipeline.business_cases.manufacturing import (
    run_manufacturing_business_case,
)
from private5g_pipeline.business_cases.pharma import run_pharma_business_case
from private5g_pipeline.portal.generate import generate_portal
from private5g_pipeline.scenarios.manufacturing import (
    run_manufacturing_agv_scenario,
)
from private5g_pipeline.scenarios.pharma import run_pharma_bioreactor_scenario


@pytest.fixture(scope="module")
def evidence_root(tmp_path_factory):
    """Build a complete reports/ tree so the portal has everything to link."""
    root = tmp_path_factory.mktemp("portal_evidence")

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

    return root


@pytest.fixture(scope="module")
def portal_html(evidence_root):
    output = evidence_root / "index.html"
    html = generate_portal(
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
    )
    return output, html


def test_portal_file_exists_and_is_html(portal_html):
    path, html = portal_html
    assert Path(path).exists()
    assert html.startswith("<!doctype html>")
    assert "</html>" in html


def test_portal_carries_headline_numbers(portal_html):
    _, html = portal_html
    # Manufacturing headline.
    assert "100 AGVs" in html
    assert "20 ms" in html
    # Pharma headline.
    assert "5 min" in html
    assert "1.00" in html


def test_portal_links_to_all_six_artifact_classes(portal_html):
    _, html = portal_html
    assert "Private 5G Edge-AI Capacity Console" in html
    assert "dashboard.html" in html
    assert "../BUSINESS_CASE.md" in html
    assert "business_cases/manufacturing_agv_capacity.md" in html
    assert "business_cases/pharma_bioreactor_anomaly.md" in html
    assert "scenarios/manufacturing_agv/dashboard_summary.md" in html
    assert "scenarios/pharma_bioreactor/dashboard_summary.md" in html
    assert "../TECH_BRIEF.md" in html
    assert "../README.md" in html


def test_portal_includes_scope_block(portal_html):
    _, html = portal_html
    # "What I tested, what I didn't" is the humanized boundary block.
    assert "What I tested, what I didn't" in html
    assert "live private 5G network" in html
    assert "seeded simulation" in html


def test_portal_is_launchpad_for_key_evidence(portal_html):
    _, html = portal_html
    expected = [
        "Start here",
        "Executive dashboard",
        "Manufacturing decision",
        "Bottleneck evidence",
        "Secondary portability",
        "Pipeline evidence",
        "Benchmarks and CI",
        "Boundaries",
        "Visual evidence",
        "Fleet ceiling: 100 AGVs stayed under 20 ms",
        "Operational Decision Summary",
        "Bottleneck Attribution",
        "Operator Action Plan",
        "Evidence vs Boundary",
    ]
    for text in expected:
        assert text in html


def test_portal_includes_plot_previews(portal_html):
    _, html = portal_html
    expected_figures = [
        "scenarios/manufacturing_agv/figures/01_latency_vs_fleet.png",
        "scenarios/manufacturing_agv/figures/02_edge_load_by_zone.png",
        "scenarios/manufacturing_agv/figures/03_budget_violation_timeline.png",
    ]
    for figure in expected_figures:
        assert figure in html


def test_portal_does_not_claim_forbidden_live_integrations(portal_html):
    _, html = portal_html
    html_without_boundaries = (
        html.replace("no MES/SCADA/PLC connector", "")
        .replace("no production deployment claim", "")
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


def test_portal_links_to_repo(portal_html):
    _, html = portal_html
    assert "github.com/obiedeh/private-5g-edge-telemetry" in html
