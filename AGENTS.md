# AGENTS.md

Repository-level operating instructions for Codex.

For shared engineering standards and skill definitions, read:

```text
https://github.com/obiedeh/obiedeh/tree/main/agent-skills
```

---

# Codex Role

Use Codex for:

- patches to `private5g_pipeline/` modules
- test generation for `tests/`
- adding CLI commands following patterns in `private5g_pipeline/cli.py`
- config and schema changes
- vertical-scenario generators under `private5g_pipeline/scenarios/`
- business-case report generators under `private5g_pipeline/business_cases/`
- dependency and packaging changes

Do not use Codex for:

- removing or renaming the canonical `private5g_pipeline/` package
- removing the `private_5g_ran_pipeline.py` back-compat wrapper without explicit Claude Code review
- adding live private-5G network integration or autonomous control logic
- adding live edge-AI / vendor-SDK integration (NVIDIA Aerial, Azure Private 5G Core, AWS Wavelength, Nokia / Siemens Industrial Edge)
- adding live OT/IT system integration (MindSphere, MES, etc.)
- adding MCP servers or external tool integrations without explicit instruction

Default workflow:

```text
Claude Code = architecture review, skill selection, planning, credibility-boundary enforcement
Codex       = implement, patch, test
Claude Code = production-readiness check before merge
```

---

# Skill Selection

- `production-architecture-reviewer`: pipeline structure changes, module boundary changes, service design
- `repo-hardening-refactor`: stale docs, notebook bloat, unused config cleanup
- `runtime-stability-debugger`: pipeline memory pressure, long-running ingestion, Parquet write failures
- `ai-ran-workflow-generator`: KPI thresholds, alert logic, vertical-scenario generation, SOP structure
- `observability-generator`: structured logging, JSON report coverage, quarantine rate metrics
- `edge-ai-deployer`: Dockerfile, containerised runs, edge deployment of the pipeline CLI

---

# Project Structure

```text
private5g_pipeline/        # Canonical Python package — all new code goes here
  ├── ingest.py            # CSV + synthetic ingestion
  ├── schema.py            # Schema validation + quarantine
  ├── transform.py         # Feature engineering, casting, QC
  ├── pipeline.py          # Top-level orchestrator
  ├── export.py            # Parquet + JSON + MD writers
  ├── visuals.py           # Matplotlib reports
  ├── streaming.py         # NDJSON event stream
  ├── metrics.py · config.py · cli.py
  └── __main__.py          # python -m private5g_pipeline
private_5g_ran_pipeline.py # 6-line back-compat wrapper calling cli.main
configs/                   # Active pipeline configs (pipeline_config.yaml)
tests/                     # Pytest suite (12 test files)
data/                      # Sample CSVs (sample_telemetry.csv committed)
reports/                   # Generated evidence packs + portal (committed)
  ├── scenarios/
  │   ├── manufacturing_agv/   # Phase 2 — vertical scenario
  │   ├── pharma_bioreactor/   # Phase 2 — vertical scenario
  │   └── latest/              # existing telco-generic scenarios
  ├── business_cases/          # Phase 3 — vertical business cases
  └── index.html               # Phase 4 — evidence portal
docs/                      # Architecture notes
notebooks/legacy/          # Original Colab notebooks (provenance only)
```

---

# Known Tech Debt

These items are tracked and require explicit instruction before changing:

- **Back-compat wrapper**: `private_5g_ran_pipeline.py` is a 6-line shim that calls
  `private5g_pipeline.cli.main`. It exists for older docs / scripts that invoke the
  script by name. Do not add logic here — extend `private5g_pipeline.cli` instead.
- **Legacy notebooks**: `notebooks/legacy/` keeps the original Colab exploration
  notebooks for provenance. They are not part of the canonical entry point and must
  not be re-introduced at the repo root.

---

# Anti-Bloat Rules

Do not create:

- new root-level Python scripts (extend `private5g_pipeline.cli` instead)
- new notebooks at the repo root (use `notebooks/legacy/` only for archived provenance)
- duplicate feature engineering helpers
- speculative live-integration modules (NVIDIA Aerial, Azure Private 5G, vendor SDKs)
- generic KPI dashboards that aren't tied to a named vertical scenario or business case

Every new file must justify at least one of:

- vertical-scenario evidence (manufacturing AGV-fleet, pharma bioreactor, …)
- business-case answer (named operational question, measured numbers, sensitivity)
- operational reliability improvement
- observability improvement
- deployment-readiness improvement

---

# Credibility Boundary (mirrors README + TECH_BRIEF)

This repo demonstrates the **private-5G + edge-AI telemetry pipeline pattern** on
synthetic telemetry. Do not introduce claims of:

- live private-5G RAN integration
- live edge-AI inference workload integration (NVIDIA Aerial, Azure Private 5G Core,
  AWS Wavelength, Nokia Industrial Edge, Siemens Industrial Edge)
- live OT/IT system integration (MindSphere, MES, …)
- production deployment lifecycle (Helm packaging, vendor SDK certifications)
- standards compliance (3GPP private-5G profiles, IEC 62443 OT security)

---

# Output Format

At the end of each task, Codex should report:

1. Files changed and why
2. Tests run
3. Tests not run and why
4. Risks or follow-up work
5. Whether Claude Code review is needed
