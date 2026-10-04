from __future__ import annotations

from pathlib import Path

import pandas as pd

from private5g_pipeline.export import (
    build_observability_report,
)
from private5g_pipeline.export import (
    write_json_report as write_report,
)
from private5g_pipeline.schema import SchemaValidationResult


def build_operator_summary(
    raw: pd.DataFrame,
    curated: pd.DataFrame,
    schema_result: SchemaValidationResult | None = None,
    quarantined: pd.DataFrame | None = None,
    top_n: int = 3,
) -> str:
    """Create a compact Markdown snapshot for operators."""
    lines: list[str] = [
        "# Private 5G Operator Summary",
        "",
        f"- Raw rows: {len(raw)}",
        f"- Curated rows: {len(curated)}",
        f"- Quarantined rows: {len(quarantined) if quarantined is not None else 0}",
    ]

    if schema_result is not None:
        lines.extend(
            [
                f"- Schema valid: {schema_result.valid}",
                f"- Schema errors: {len(schema_result.errors)}",
                f"- Schema warnings: {len(schema_result.warnings)}",
            ]
        )

    if "congestion_ratio" in curated.columns and len(curated):
        congested = curated.sort_values("congestion_ratio", ascending=False).head(top_n)
        lines.extend(["", "## Top Congested Cells"])
        for _, row in congested.iterrows():
            lines.append(
                f"- {row['cell_id']} / {row['slice_type']} / {row['hour']}: "
                f"congestion={row['congestion_ratio']:.2f}, "
                f"latency_p95={row.get('latency_ms_p95', float('nan')):.2f} ms"
            )
    else:
        lines.extend(["", "## Top Congested Cells", "- No congestion data available."])

    if "latency_ms_p95" in curated.columns and len(curated):
        worst_latency = curated.sort_values("latency_ms_p95", ascending=False).head(top_n)
        lines.extend(["", "## Worst Latency Slices"])
        for _, row in worst_latency.iterrows():
            lines.append(
                f"- {row['cell_id']} / {row['slice_type']} / {row['hour']}: "
                f"latency_p95={row['latency_ms_p95']:.2f} ms"
            )
    else:
        lines.extend(["", "## Worst Latency Slices", "- No latency data available."])

    return "\n".join(lines) + "\n"


def write_operator_summary(summary: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary, encoding="utf-8")


# Re-export aliases kept for callers that imported these from metrics directly.
# Prefer importing from private5g_pipeline.export directly in new code.
__all__ = [
    "build_observability_report",
    "write_report",
    "build_operator_summary",
    "write_operator_summary",
]
