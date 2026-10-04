"""Generate ``reports/index.html`` from the committed evidence packs.

Single static page with cards for:
* Tech brief + README
* Manufacturing AGV business case (headline + sensitivity)
* Pharma bioreactor business case (headline + sensitivity)
* Manufacturing scenario evidence pack
* Pharma scenario evidence pack
* Schema-typed ingestion + fail-soft quarantine
* Reproducibility & test suite

Headline numbers in the cards are pulled live from the metrics JSONs so
the portal stays in sync with the evidence.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from private5g_pipeline.portal.ee_theme import apply_theme

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = "reports/index.html"

_MANUFACTURING_METRICS = "reports/scenarios/manufacturing_agv/scenario_metrics.json"
_PHARMA_METRICS = "reports/scenarios/pharma_bioreactor/scenario_metrics.json"
_MANUFACTURING_SENSITIVITY = (
    "reports/business_cases/manufacturing_agv_sensitivity.json"
)
_PHARMA_SENSITIVITY = "reports/business_cases/pharma_bioreactor_sensitivity.json"


_STYLE = """
:root {
  --bg: #f6f7f3;
  --panel: #ffffff;
  --line: #d8dbd2;
  --text: #1a1c1e;
  --muted: #5d6459;
  --blue: #1f6fd1;
  --red: #c62828;
}
body {
  margin: 0;
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  color: var(--text);
  background:
    linear-gradient(180deg, rgba(31, 111, 209, 0.10), rgba(248, 250, 252, 0.0) 240px),
    var(--bg);
}
.wrap { max-width: 1400px; margin: 0 auto; padding: 28px; }
h1 { margin: 0 0 8px; font-size: 34px; }
.sub { color: var(--muted); max-width: 960px; line-height: 1.55; }
.story {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 20px;
  margin-top: 18px;
  max-width: 1040px;
}
.story h2 { margin: 0 0 8px; font-size: 20px; }
.story p { color: var(--muted); line-height: 1.55; margin: 8px 0; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 22px; }
.visual-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 22px; }
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: 0 1px 2px rgba(26, 28, 30, 0.04);
}
.eyebrow {
  color: var(--blue);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.card h3 { margin: 6px 0 4px; font-size: 18px; }
.card p { color: var(--muted); line-height: 1.55; margin: 8px 0 12px; }
.plot-card img {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  margin: 10px 0 8px;
}
.plot-card a.source { display: inline-block; margin-top: 4px; font-size: 13px; }
.metric {
  display: inline-block;
  background: rgba(31, 111, 209, 0.08);
  color: var(--blue);
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 13px;
  margin-right: 6px;
}
.metric.warn { background: rgba(192, 74, 74, 0.10); color: var(--red); }
ul { padding-left: 18px; margin: 6px 0 0; }
li { margin: 6px 0; }
.thumbs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin: 12px 0 14px;
}
.thumbs img {
  width: 100%;
  height: auto;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: #fff;
}
a { color: var(--blue); text-decoration: none; }
a:hover { text-decoration: underline; }
.footer {
  margin-top: 22px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.55;
}
.boundary {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 20px;
  margin-top: 22px;
}
.boundary h3 { margin: 0 0 6px; font-size: 16px; }
@media (max-width: 880px) {
  .grid { grid-template-columns: 1fr; }
  .visual-grid { grid-template-columns: 1fr; }
}
"""


def _read_json(path: str) -> dict[str, Any]:
    data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object at {path}, got {type(data).__name__}")
    return data


def _format_lead_time(value: Any) -> str:
    if value is None:
        return "not detected"
    return f"{float(value):.0f} min"


def _format_precision(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}"


def _card(
    eyebrow: str,
    title: str,
    description: str,
    metrics: list[tuple[str, str]],
    links: list[tuple[str, str]],
) -> str:
    metric_html = "".join(
        f'<span class="metric{" warn" if cls else ""}">{label}</span>'
        for cls, label in (
            (False, f"{key}: {val}") for key, val in metrics
        )
    ) if metrics else ""

    links_html = (
        "<ul>"
        + "".join(f'<li><a href="{href}">{text}</a></li>' for text, href in links)
        + "</ul>"
        if links
        else ""
    )
    return (
        '<section class="card">'
        f'<div class="eyebrow">{eyebrow}</div>'
        f"<h3>{title}</h3>"
        f"<p>{description}</p>"
        f"{metric_html}"
        f"{links_html}"
        "</section>"
    )


def _plot_card(title: str, image: str, interpretation: str, href: str) -> str:
    return (
        '<section class="card plot-card">'
        '<div class="eyebrow">Visual evidence</div>'
        f"<h3>{title}</h3>"
        f'<a href="{href}"><img src="{image}" alt="{title}"></a>'
        f"<p>{interpretation}</p>"
        f'<a class="source" href="{href}">Open source artifact</a>'
        "</section>"
    )


def _visual_summary() -> str:
    cards = [
        _plot_card(
            "Fleet ceiling: 100 AGVs stayed under 20 ms",
            "scenarios/manufacturing_agv/figures/01_latency_vs_fleet.png",
            "Worst-cell hourly p95 latency stays below the control-loop budget through the 100-AGV scenario.",
            "dashboard.html",
        ),
        _plot_card(
            "120 AGVs crossed the latency budget",
            "scenarios/manufacturing_agv/figures/03_budget_violation_timeline.png",
            "Per-sample latency readings show the over-budget cloud once the tested fleet reaches the unsafe expansion band.",
            "scenarios/manufacturing_agv/figures/03_budget_violation_timeline.png",
        ),
        _plot_card(
            "Assembly-zone GPU saturation appeared first",
            "scenarios/manufacturing_agv/figures/02_edge_load_by_zone.png",
            "The assembly zone carries the pressure signal in this seeded simulation, which points the next test toward edge capacity and workload balance.",
            "scenarios/manufacturing_agv/figures/02_edge_load_by_zone.png",
        ),
    ]
    return '<div class="visual-grid">' + "\n".join(cards) + "</div>"


def _evidence_boundary_launchpad() -> str:
    evidence = [
        "seeded AGV fleet simulation",
        "worst-cell p95 latency budget check",
        "edge GPU saturation signal",
        "schema validation and quarantine behavior",
        "deterministic regeneration",
        "benchmark and CI validation",
    ]
    boundaries = [
        "no live private 5G network",
        "no vendor RAN integration",
        "no MES/SCADA/PLC connector",
        "no production deployment claim",
        "no safety certification claim",
        "no real AGV fleet telemetry",
    ]
    return (
        '<section class="boundary">'
        "<h3>Evidence vs Boundary</h3>"
        '<div class="grid">'
        "<div><strong>Evidence demonstrated</strong><ul>"
        + "".join(f"<li>{item}</li>" for item in evidence)
        + "</ul></div><div><strong>Boundary preserved</strong><ul>"
        + "".join(f"<li>{item}</li>" for item in boundaries)
        + "</ul></div></div></section>"
    )


def _start_here_card(metrics: dict[str, Any]) -> str:
    return _card(
        eyebrow="Start here",
        title="Executive dashboard",
        description=(
            "Open the operator console first. It answers the AGV capacity question, "
            "shows the first unsafe expansion point, attributes the likely bottleneck, "
            "and keeps deployment boundaries visible."
        ),
        metrics=[
            ("ceiling", f"{metrics['max_fleet_under_budget']} AGVs"),
            ("budget", f"{float(metrics['latency_budget_ms']):.0f} ms"),
        ],
        links=[
            ("Open dashboard", "dashboard.html"),
            ("Operational Decision Summary", "dashboard.html"),
            ("Bottleneck Attribution", "dashboard.html"),
            ("Operator Action Plan", "dashboard.html"),
            ("Evidence vs Boundary", "dashboard.html"),
        ],
    )


def _manufacturing_decision_card(metrics: dict[str, Any]) -> str:
    unsafe = next(
        (
            int(row["fleet_size"])
            for row in sorted(metrics["summary"], key=lambda r: int(r["fleet_size"]))
            if row["budget_violated"]
        ),
        None,
    )
    return _card(
        eyebrow="Manufacturing decision",
        title="AGV capacity and 20 ms budget",
        description=(
            f"The seeded manufacturing sweep keeps worst-cell p95 latency under "
            f"{float(metrics['latency_budget_ms']):.0f} ms through "
            f"{metrics['max_fleet_under_budget']} AGVs. The first tested unsafe "
            f"expansion point is {unsafe} AGVs."
        ),
        metrics=[
            ("recommended ceiling", f"{metrics['max_fleet_under_budget']} AGVs"),
            ("first unsafe", f"{unsafe} AGVs"),
        ],
        links=[
            ("Business case", "business_cases/manufacturing_agv_capacity.md"),
            ("Scenario summary", "scenarios/manufacturing_agv/dashboard_summary.md"),
            ("Scenario metrics", "scenarios/manufacturing_agv/scenario_metrics.json"),
            ("Fleet summary CSV", "scenarios/manufacturing_agv/fleet_summary.csv"),
        ],
    )


def _bottleneck_evidence_card() -> str:
    return _card(
        eyebrow="Bottleneck evidence",
        title="Edge GPU / worst-cell p95 analysis",
        description=(
            "Manufacturing evidence links the 20 ms breach to worst-cell latency growth "
            "and simulated edge-load pressure in the assembly zone. This is a likely "
            "bottleneck candidate, not live factory attribution."
        ),
        metrics=[],
        links=[
            ("Latency vs fleet", "scenarios/manufacturing_agv/figures/01_latency_vs_fleet.png"),
            ("Edge load by zone", "scenarios/manufacturing_agv/figures/02_edge_load_by_zone.png"),
            ("Budget violation timeline", "scenarios/manufacturing_agv/figures/03_budget_violation_timeline.png"),
            ("Bottleneck attribution JSON", "bottleneck_attribution.json"),
        ],
    )


def _secondary_pharma_card(metrics: dict[str, Any]) -> str:
    default = metrics["default_result"]
    return _card(
        eyebrow="Secondary portability",
        title="Pharma scenario",
        description=(
            "Secondary portability scenario, not the headline use case. It shows the same "
            "pipeline shape on a seeded bioreactor anomaly simulation; it does not use real "
            "pharmaceutical plant telemetry."
        ),
        metrics=[
            ("lead time", _format_lead_time(default["lead_time_minutes"])),
            ("precision", _format_precision(default["precision"])),
        ],
        links=[
            ("Business case", "business_cases/pharma_bioreactor_anomaly.md"),
            ("Scenario summary", "scenarios/pharma_bioreactor/dashboard_summary.md"),
            ("Scenario metrics", "scenarios/pharma_bioreactor/scenario_metrics.json"),
        ],
    )


def _pipeline_evidence_card() -> str:
    return _card(
        eyebrow="Pipeline evidence",
        title="Schema validation, quarantine, deterministic generation",
        description=(
            "The telemetry layer validates schema, fails soft into quarantine for bad rows, "
            "and regenerates deterministic seeded artifacts through the same static report flow."
        ),
        metrics=[],
        links=[
            ("Architecture", "../docs/ARCHITECTURE.md"),
            ("Sample pipeline report", "sample_pipeline_report.md"),
            ("Tests", "../tests/"),
            ("Makefile verification", "../Makefile"),
        ],
    )


def _benchmark_launchpad_card() -> str:
    return _card(
        eyebrow="Benchmarks and CI",
        title="Performance and reproducibility proof",
        description=(
            "Benchmarks focus on telemetry-pipeline evidence: ingest throughput, quarantine "
            "throughput, end-to-end regeneration time, and deterministic artifact hashes."
        ),
        metrics=[],
        links=[
            ("Benchmarks", "benchmarks.md"),
            ("Raw benchmark JSON", "benchmarks.json"),
            ("CI workflow", "../.github/workflows/ci.yml"),
        ],
    )


def _boundaries_card() -> str:
    return _card(
        eyebrow="Boundaries",
        title="What this project does not claim",
        description=(
            "No live private 5G network, no vendor RAN integration, no MES/SCADA/PLC "
            "connector, no safety certification, no production runtime claim, and no real "
            "AGV fleet telemetry."
        ),
        metrics=[],
        links=[
            ("Operator console readiness", "operator_console_readiness.json"),
            ("README boundary", "../README.md"),
        ],
    )


def _manufacturing_card(metrics: dict[str, Any], sensitivity: dict[str, Any] | None) -> str:
    max_fleet = metrics["max_fleet_under_budget"]
    budget = float(metrics["latency_budget_ms"])
    n_cells = int(metrics["n_cells"])

    card_metrics = [
        ("max fleet", f"{max_fleet} AGVs"),
        ("budget", f"{budget:.0f} ms"),
        ("cells", str(n_cells)),
    ]

    if sensitivity is not None:
        rows = sorted(
            sensitivity["budget_sensitivity"], key=lambda r: r["latency_budget_ms"]
        )
        if rows:
            card_metrics.append(
                ("sensitivity", f"{rows[0]['max_fleet_under_budget']} → {rows[-1]['max_fleet_under_budget']} AGVs across budgets")
            )

    description = (
        f"Ops wants to grow the AGV fleet. On this simulation, the largest fleet that keeps "
        f"worst-cell p95 latency under the {budget:.0f} ms budget is "
        f"<strong>{max_fleet} AGVs</strong>. The assembly zone hits saturation first &mdash; "
        f"busiest zone, GPU runs out of room before paint or warehouse do."
        '<div class="thumbs">'
        '<a href="scenarios/manufacturing_agv/figures/01_latency_vs_fleet.png">'
        '<img src="scenarios/manufacturing_agv/figures/01_latency_vs_fleet.png" '
        'alt="Worst-cell p95 latency vs fleet size; budget crossover at 100 → 120 AGVs"/></a>'
        '<a href="scenarios/manufacturing_agv/figures/02_edge_load_by_zone.png">'
        '<img src="scenarios/manufacturing_agv/figures/02_edge_load_by_zone.png" '
        'alt="Edge GPU load by factory zone; assembly saturates first"/></a>'
        '<a href="scenarios/manufacturing_agv/figures/03_budget_violation_timeline.png">'
        '<img src="scenarios/manufacturing_agv/figures/03_budget_violation_timeline.png" '
        'alt="Per-sample latency over the fleet sweep; budget breaches in red"/></a>'
        "</div>"
    )

    links = [
        ("Business case (1 page)", "business_cases/manufacturing_agv_capacity.md"),
        ("Sensitivity JSON", "business_cases/manufacturing_agv_sensitivity.json"),
        ("Scenario dashboard", "scenarios/manufacturing_agv/dashboard_summary.md"),
        ("Scenario metrics", "scenarios/manufacturing_agv/scenario_metrics.json"),
    ]
    return _card(
        eyebrow="Manufacturing · AGV-fleet capacity",
        title="How many AGVs can the floor add?",
        description=description,
        metrics=card_metrics,
        links=links,
    )


def _pharma_card(metrics: dict[str, Any], sensitivity: dict[str, Any] | None) -> str:
    default = metrics["default_result"]
    lead = _format_lead_time(default["lead_time_minutes"])
    prec = _format_precision(default["precision"])
    threshold = float(metrics["default_threshold"])

    card_metrics = [
        ("lead time", lead),
        ("precision", prec),
        ("threshold", f"z = {threshold:.1f}"),
    ]

    if sensitivity is not None:
        seeds = sensitivity.get("seed_sensitivity", [])
        detected = sum(1 for r in seeds if r.get("detected"))
        if seeds:
            card_metrics.append(
                ("seed stability", f"{detected}/{len(seeds)} seeds detect")
            )

    description = (
        "To show the pipeline isn't single-use, I point it at a non-manufacturing "
        "vertical: a pharma cleanroom bioreactor with slow sensor drift through the "
        f"shift and an injected contamination event late in the day. Detector fires "
        f"<strong>{lead} after onset</strong> at <strong>precision {prec}</strong>. "
        "Same code path as the manufacturing scenario; different simulator and detector "
        "tune. The headline audience for this repo is Industry 4.0 — this cameo is just "
        "evidence that the pipeline is portable."
        '<div class="thumbs">'
        '<a href="scenarios/pharma_bioreactor/figures/01_signal_timeline.png">'
        '<img src="scenarios/pharma_bioreactor/figures/01_signal_timeline.png" '
        'alt="Edge × latency signal across 24 hours with event window shaded"/></a>'
        '<a href="scenarios/pharma_bioreactor/figures/02_detector_zscore.png">'
        '<img src="scenarios/pharma_bioreactor/figures/02_detector_zscore.png" '
        'alt="Detector z-score over the day; spike at event onset"/></a>'
        '<a href="scenarios/pharma_bioreactor/figures/03_threshold_sweep.png">'
        '<img src="scenarios/pharma_bioreactor/figures/03_threshold_sweep.png" '
        'alt="Lead time vs precision across threshold sweep"/></a>'
        "</div>"
    )

    links = [
        ("Business case (1 page)", "business_cases/pharma_bioreactor_anomaly.md"),
        ("Sensitivity JSON", "business_cases/pharma_bioreactor_sensitivity.json"),
        ("Scenario dashboard", "scenarios/pharma_bioreactor/dashboard_summary.md"),
        ("Scenario metrics", "scenarios/pharma_bioreactor/scenario_metrics.json"),
    ]
    return _card(
        eyebrow="Portability cameo · Pharma bioreactor",
        title="Same pipeline, different vertical",
        description=description,
        metrics=card_metrics,
        links=links,
    )


def _scenario_pack_card_manufacturing() -> str:
    return _card(
        eyebrow="Evidence pack",
        title="The data behind the AGV answer",
        description=(
            "Everything that produced the 100-AGV number. The raw simulated telemetry "
            "as CSV, the hourly KPIs after curation, the per-fleet summary table, and "
            "three figures: latency-vs-fleet bars with the budget line drawn in, edge "
            "GPU load by zone, and a sample-level timeline of budget breaches."
        ),
        metrics=[],
        links=[
            ("Dashboard summary", "scenarios/manufacturing_agv/dashboard_summary.md"),
            ("Telemetry CSV", "scenarios/manufacturing_agv/telemetry.csv"),
            ("Hourly KPIs CSV", "scenarios/manufacturing_agv/hourly_kpis.csv"),
            ("Fleet summary CSV", "scenarios/manufacturing_agv/fleet_summary.csv"),
        ],
    )


def _scenario_pack_card_pharma() -> str:
    return _card(
        eyebrow="Evidence pack",
        title="The data behind the bioreactor answer",
        description=(
            "Everything that produced the 5-minute lead time. The 24 hours of simulated "
            "telemetry as CSV, the hourly curated KPIs, the threshold-sweep table, and "
            "three figures: the edge-load × latency signal across the day with the "
            "event window shaded, the detector's z-score trace, and the lead-time vs "
            "precision sweep across thresholds."
        ),
        metrics=[],
        links=[
            ("Dashboard summary", "scenarios/pharma_bioreactor/dashboard_summary.md"),
            ("Telemetry CSV", "scenarios/pharma_bioreactor/telemetry.csv"),
            ("Hourly KPIs CSV", "scenarios/pharma_bioreactor/hourly_kpis.csv"),
            ("Threshold sweep CSV", "scenarios/pharma_bioreactor/threshold_sweep.csv"),
        ],
    )


def _stack_mapping_card() -> str:
    return _card(
        eyebrow="Where this fits",
        title="The layered Industry 4.0 stack",
        description=(
            "This is context, not an integration claim. This telemetry layer sits "
            "<em>between</em> private-5G-style KPIs, edge-AI workload health, and factory "
            "operations, producing operational answers above."
            "<br><br>"
            "<strong>AI compute &amp; edge AI</strong> &mdash; edge GPU load, inference pressure, "
            "and queueing headroom."
            "<br>"
            "<strong>Private 5G &amp; industrial wireless</strong> &mdash; cell and slice KPIs, "
            "drop rate, handovers, jitter, and latency."
            "<br>"
            "<strong>Factory operations</strong> &mdash; AGV fleet size, zone-level workload, "
            "and control-loop budget."
            "<br>"
            "<strong>Decision layer</strong> &mdash; capacity ceiling, bottleneck attribution, "
            "sensitivity, and evidence boundaries."
            "<br><br>"
            "Nothing here claims integration with vendor deployments."
        ),
        metrics=[],
        links=[
            ("Full mapping in the brief", "../TECH_BRIEF.md#where-this-fits-in-the-stack"),
            ("Full mapping in the README", "../README.md#where-this-fits-in-the-stack"),
        ],
    )


def _what_makes_this_hard_card() -> str:
    return _card(
        eyebrow="What actually makes this hard",
        title="Bottlenecks addressed vs deferred",
        description=(
            "Across the AI + private-5G partnerships forming now, the bottleneck isn't model "
            "accuracy. It's the integration seam between layers. This repo speaks to three "
            "honestly, and defers three to the boundary block."
            "<br><br>"
            "<strong>Addressed.</strong> "
            "<em>Latency determinism</em>: the 100-AGV answer is the latency-determinism "
            "question (worst-cell p95 vs the 20 ms budget). "
            "<em>Data governance</em>: schema-typed ingest with fail-soft quarantine, tested "
            "under corrupted fixtures. "
            "<em>Runtime stability</em>: deterministic seeded simulators, <code>make verify</code> "
            "chains the gate, CI runs it on every push."
            "<br><br>"
            "<strong>Deferred.</strong> OT / SCADA / PLC / MES integration. Safety "
            "certification (IEC 62443, IEC 61508). Continuous production-load runtime."
        ),
        metrics=[],
        links=[
            ("Full table in the brief", "../TECH_BRIEF.md#what-actually-makes-this-hard"),
            ("Full table in the README", "../README.md#what-actually-makes-this-hard"),
        ],
    )


def _pipeline_pattern_card() -> str:
    return _card(
        eyebrow="The platform underneath",
        title="One pipeline, two industries",
        description=(
            "Same code path for both stories. Raw telemetry arrives, the schema "
            "validates it, rows that don't conform go to a quarantine sink so the "
            "pipeline doesn't crash on bad data. Clean rows get clipped to sane ranges, "
            "edge-AI features get computed, then aggregated to hourly KPIs per cell "
            "and slice. Both scenarios are just different inputs into this."
        ),
        metrics=[],
        links=[
            ("Schema module", "../private5g_pipeline/schema.py"),
            ("Transform module", "../private5g_pipeline/transform.py"),
            ("Pipeline module", "../private5g_pipeline/pipeline.py"),
            ("Sample run report", "sample_pipeline_report.md"),
        ],
    )


def _tech_brief_card() -> str:
    return _card(
        eyebrow="Start here",
        title="One-page brief",
        description=(
            "Both buyer stories side-by-side, the answers, the sensitivity, what I "
            "tested, and what I did not claim. Five minutes to read for an engineering leader or "
            "executive who wants the shape of the work before going deeper."
        ),
        metrics=[],
        links=[
            ("TECH_BRIEF.md", "../TECH_BRIEF.md"),
            ("README.md", "../README.md"),
            ("HOWTO.md", "../HOWTO.md"),
        ],
    )


def _reproducibility_card() -> str:
    return _card(
        eyebrow="How I know it holds",
        title="Same seed, same answer",
        description=(
            "Every simulation takes a seed. Running it twice at the same seed produces "
            "byte-identical metrics and summary CSVs &mdash; SHA-256 verified. The pharma "
            "and manufacturing headlines hold across four different seeds. The answer is "
            "the model, not the noise. Tests cover all of this and run on every push."
        ),
        metrics=[
            ("tests", "119 passing"),
            ("ci", "green"),
            ("determinism", "byte-identical"),
        ],
        links=[
            ("CI workflow", "../.github/workflows/ci.yml"),
            ("Tests directory", "../tests/"),
            ("Makefile targets", "../Makefile"),
        ],
    )


def _benchmarks_card() -> str:
    return _card(
        eyebrow="Measured numbers",
        title="Pipeline benchmarks",
        description=(
            "Not FPS or GPU utilisation &mdash; this isn't an inference workload. The "
            "benchmarks that <em>are</em> meaningful for a telemetry-intelligence layer: "
            "synthetic-generator throughput, schema-quarantine throughput under corrupted "
            "input, end-to-end regeneration wall-clock, and a SHA-256 determinism check. "
            "Refreshed by <code>make benchmarks</code>."
        ),
        metrics=[
            ("ingest", "13K rows/s"),
            ("quarantine", "104K rows/s"),
            ("regen", "11.6 s"),
            ("determinism", "byte-identical"),
        ],
        links=[
            ("Methodology + raw numbers", "benchmarks.md"),
            ("Raw JSON", "benchmarks.json"),
        ],
    )


def generate_portal(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    manufacturing_metrics_path: str = _MANUFACTURING_METRICS,
    pharma_metrics_path: str = _PHARMA_METRICS,
    manufacturing_sensitivity_path: str | None = _MANUFACTURING_SENSITIVITY,
    pharma_sensitivity_path: str | None = _PHARMA_SENSITIVITY,
) -> str:
    """Render the evidence portal and write it to ``output_path``.

    Returns the rendered HTML string.
    """
    manufacturing = _read_json(manufacturing_metrics_path)
    pharma = _read_json(pharma_metrics_path)

    if manufacturing_sensitivity_path and Path(manufacturing_sensitivity_path).exists():
        _read_json(manufacturing_sensitivity_path)

    if pharma_sensitivity_path and Path(pharma_sensitivity_path).exists():
        _read_json(pharma_sensitivity_path)

    cards = [
        _start_here_card(manufacturing),
        _manufacturing_decision_card(manufacturing),
        _bottleneck_evidence_card(),
        _secondary_pharma_card(pharma),
        _pipeline_evidence_card(),
        _benchmark_launchpad_card(),
        _boundaries_card(),
        _card(
            eyebrow="Business case",
            title="Capacity decision brief",
            description=(
                "A direct business-case note for the practical decision: avoid unsafe "
                "AGV expansion, avoid buying the wrong capacity layer first, and validate "
                "headroom with live telemetry before deployment."
            ),
            metrics=[],
            links=[("BUSINESS_CASE.md", "../BUSINESS_CASE.md")],
        ),
        _tech_brief_card(),
    ]

    html = (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8" />\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        "  <title>Private 5G Edge-AI Capacity Console</title>\n"
        f"  <style>{_STYLE}</style>\n"
        "</head>\n"
        "<body>\n"
        '  <div class="wrap">\n'
        "    <h1>Private 5G Edge-AI Capacity Console</h1>\n"
        '    <div class="sub">\n'
        "      I built a reproducible telemetry system to test when AGV fleet growth "
        "breaks a 20 ms control-loop budget.\n"
        "    </div>\n"
        '    <section class="story">\n'
        "      <h2>The factory question</h2>\n"
        "      <p>I built this project around one practical factory question: how far can a private 5G floor scale its AGV fleet before the 20 ms control-loop budget breaks?</p>\n"
        "      <p>The simulated floor stayed under budget through <strong>100 AGVs</strong>. At <strong>120 AGVs</strong>, the budget broke. The first constraint was not simply radio capacity; assembly-zone edge GPU saturation appeared first in the seeded outputs.</p>\n"
        "      <p>That changes the decision: cap expansion at 100 AGVs, rebalance assembly-zone workload, reserve edge GPU capacity before testing 120 AGVs, and validate with live RAN and GPU telemetry before any real deployment decision.</p>\n"
        "    </section>\n"
        + _visual_summary()
        + '    <div class="grid">\n'
        + "\n".join(cards)
        + "\n    </div>\n"
        + _evidence_boundary_launchpad()
        + '    <div class="boundary">\n'
        "      <h3>What I tested, what I didn't</h3>\n"
        "      <p>Every number on this page comes from a seeded simulation. I didn't "
        "connect to a live private 5G network, vendor RAN, vendor edge-AI platform, "
        "MES, SCADA, PLC, or a real AGV fleet. What's portable is the schema, the "
        "scenario pattern, and the way the capacity answer comes with its sensitivity "
        "story attached.</p>\n"
        "    </div>\n"
        '    <div class="footer">\n'
        '      Source: <a href="https://github.com/obiedeh/private-5g-edge-telemetry">'
        "github.com/obiedeh/private-5g-edge-telemetry</a>\n"
        "    </div>\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )

    html = apply_theme(html, repo_url="https://github.com/obiedeh/private-5g-edge-telemetry", dark={}, root_selectors=":root", force_dark=False, scheme="light")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    logger.info("Wrote evidence portal: %s (%d bytes)", out, len(html))
    return html
