"""Evidence-surface generators for the private 5G + edge-AI telemetry pipeline.

Two surfaces are rendered from the committed metrics + figure files:

* ``reports/index.html`` — card-grid portal, navigation-shaped.
* ``reports/dashboard.html`` — single-page executive-technical dashboard
  with inline figures, big-number callouts, and embedded sensitivity tables.

Both pull headline numbers live from the committed metrics JSONs so they
cannot drift out of sync with the underlying evidence.
"""

from __future__ import annotations

from private5g_pipeline.portal.dashboard import (
    DEFAULT_OUTPUT_PATH as DASHBOARD_DEFAULT_OUTPUT_PATH,
)
from private5g_pipeline.portal.dashboard import (
    generate_dashboard,
)
from private5g_pipeline.portal.generate import (
    DEFAULT_OUTPUT_PATH,
    generate_portal,
)

__all__ = [
    "DASHBOARD_DEFAULT_OUTPUT_PATH",
    "DEFAULT_OUTPUT_PATH",
    "generate_dashboard",
    "generate_portal",
]
