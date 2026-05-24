PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: install install-dev test lint typecheck run-sample \
        scenario-manufacturing scenario-pharma scenarios \
        business-case-manufacturing business-case-pharma business-cases \
        portal dashboard benchmarks verify

install: install-dev

install-dev:
	$(PIP) install -e . -r requirements-dev.txt

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy private5g_pipeline

run-sample:
	$(PYTHON) -m private5g_pipeline --config configs/pipeline_config.yaml

scenario-manufacturing:
	$(PYTHON) -m private5g_pipeline.scenarios --vertical manufacturing

scenario-pharma:
	$(PYTHON) -m private5g_pipeline.scenarios --vertical pharma

scenarios: scenario-manufacturing scenario-pharma

business-case-manufacturing:
	$(PYTHON) -m private5g_pipeline.business_cases --case manufacturing

business-case-pharma:
	$(PYTHON) -m private5g_pipeline.business_cases --case pharma

business-cases: business-case-manufacturing business-case-pharma

portal:
	$(PYTHON) -m private5g_pipeline.portal --target portal

dashboard:
	$(PYTHON) -m private5g_pipeline.portal --target dashboard

benchmarks:
	$(PYTHON) -m private5g_pipeline.benchmarks

# Full reproduction gate: lint + typecheck + tests + regenerate every
# committed evidence artifact + verify each one exists on disk. This is
# the same recipe CI runs on every push; running it locally before a
# commit catches drift fast.
verify: lint typecheck test scenarios business-cases portal dashboard benchmarks
	@test -f TECH_BRIEF.md
	@test -f reports/index.html
	@test -f reports/dashboard.html
	@test -f reports/benchmarks.md
	@test -f reports/benchmarks.json
	@test -f reports/scenarios/manufacturing_agv/dashboard_summary.md
	@test -f reports/scenarios/manufacturing_agv/scenario_metrics.json
	@test -f reports/scenarios/manufacturing_agv/telemetry.csv
	@test -f reports/scenarios/manufacturing_agv/fleet_summary.csv
	@test -f reports/scenarios/pharma_bioreactor/dashboard_summary.md
	@test -f reports/scenarios/pharma_bioreactor/scenario_metrics.json
	@test -f reports/scenarios/pharma_bioreactor/telemetry.csv
	@test -f reports/scenarios/pharma_bioreactor/threshold_sweep.csv
	@test -f reports/business_cases/manufacturing_agv_capacity.md
	@test -f reports/business_cases/manufacturing_agv_sensitivity.json
	@test -f reports/business_cases/pharma_bioreactor_anomaly.md
	@test -f reports/business_cases/pharma_bioreactor_sensitivity.json
	@echo "[verify] all gates green; all evidence artifacts present"
