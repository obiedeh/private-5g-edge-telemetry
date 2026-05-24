# How to run the Private 5G Edge AI Telemetry pipeline

Step-by-step recipes for installation, config-driven runs, vertical scenarios, business case reports, and tests.

## 1. Create and activate a virtual environment

```bash
# Linux / macOS
python -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 2. Install runtime + dev dependencies

```bash
pip install -e . -r requirements-dev.txt
```

## 3. Run the pipeline against the sample CSV

```bash
python -m private5g_pipeline --config configs/pipeline_config.yaml
```

Equivalent shorthand (when you don't have a config and want a synthetic run):

```bash
python -m private5g_pipeline --generate_synthetic --output_parquet data/curated/private5g_kpis.parquet
```

## 4. Generate the sample evidence bundle

```bash
make run-sample
```

Writes the curated Parquet, observability JSON, operator summary Markdown, and visual report under `reports/`.

## 5. Run the vertical scenarios

Manufacturing AGV-fleet scenario:

```bash
make scenario-manufacturing
```

Pharma bioreactor-anomaly scenario:

```bash
make scenario-pharma
```

Each writes a self-contained evidence pack to `reports/scenarios/<vertical>/` with telemetry, metrics, plots, and a `dashboard_summary.md`.

## 6. Build the business case reports

```bash
make business-cases
```

Two Markdown reports + their raw sensitivity JSONs under `reports/business_cases/`:

- `manufacturing_agv_capacity.md` — *"Can the factory handle N more AGVs without violating the 20 ms latency budget?"* (answer: 100 AGVs; with budget + fine-grained + seed sensitivity)
- `pharma_bioreactor_anomaly.md` — *"How early can we detect a bioreactor anomaly, and at what precision?"* (answer: 5 min lead time at precision 1.00; with threshold + seed sensitivity)

Each business case re-runs its scenario into a tmpdir at three parameter
variations and a small set of alternate seeds, then aggregates the headline
metrics into a single one-page report. The canonical scenario evidence pack
under `reports/scenarios/<vertical>/` provides the headline answer; the
sensitivity sweep adds the operational context.

## 7. Build the evidence portal

```bash
make portal
```

Renders `reports/index.html` from the committed scenario + business-case
metrics JSONs. The portal cards pull the headline numbers live so the page
cannot drift out of sync with the underlying evidence. Open the file
directly in a browser, or serve it via GitHub Pages.

## 8. Full reproduction gate

```bash
make verify
```

Runs the same recipe CI runs on every push: ruff lint → mypy → pytest →
regenerate both scenarios → regenerate both business cases → regenerate
the portal → check every committed evidence artifact still exists. Use
this before pushing a change to confirm nothing has drifted.

## 9. Run tests

```bash
make test
```

CI runs the same recipe on Ubuntu / Python 3.11. See `.github/workflows/ci.yml`.

## 10. Direct programmatic use (Python)

```python
from private5g_pipeline.config import PipelineConfig
from private5g_pipeline.pipeline import run_pipeline_config

config = PipelineConfig()
config.ingestion.mode = "synthetic"
config.export.output_parquet = "data/curated/sample.parquet"
result = run_pipeline_config(config)
print(result)
```

## Troubleshooting

- `ModuleNotFoundError: private5g_pipeline` → make sure you ran `pip install -e .` inside the active venv.
- Parquet write errors → `pip install pyarrow`.
- For notebook workflows prefer calling `run_pipeline_config()` programmatically rather than `cli.main()` to avoid argparse interference. The legacy exploration notebooks under `notebooks/legacy/` are kept for reference only — they are not part of the canonical entry point.

## Legacy entry point

The repo retains a 6-line shim at `private_5g_ran_pipeline.py` that calls `private5g_pipeline.cli.main`. It exists so older docs / scripts referencing the script name still work. New work should use `python -m private5g_pipeline` directly.
