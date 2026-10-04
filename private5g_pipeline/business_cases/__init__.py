"""Vertical business-case generators.

Each business case asks one operational question, surfaces the measured
answer from the canonical scenario evidence pack, and adds a sensitivity
table built by re-running the scenario at parameter variations.

The output is a single Markdown report per vertical under
``reports/business_cases/``, plus a JSON file with the raw sensitivity
numbers so the table can be regenerated without re-running anything.

Business-case modules call the existing scenario runners — they do not
re-implement the simulated telemetry models.
"""

from __future__ import annotations

from private5g_pipeline.business_cases.manufacturing import (
    DEFAULT_OUTPUT_DIR as MANUFACTURING_BUSINESS_CASE_DIR,
)
from private5g_pipeline.business_cases.manufacturing import (
    run_manufacturing_business_case,
)
from private5g_pipeline.business_cases.pharma import (
    DEFAULT_OUTPUT_DIR as PHARMA_BUSINESS_CASE_DIR,
)
from private5g_pipeline.business_cases.pharma import (
    run_pharma_business_case,
)

__all__ = [
    "MANUFACTURING_BUSINESS_CASE_DIR",
    "PHARMA_BUSINESS_CASE_DIR",
    "run_manufacturing_business_case",
    "run_pharma_business_case",
]
