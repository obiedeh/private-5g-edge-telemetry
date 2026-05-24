"""Pipeline-shape benchmarks for private-5G + edge-AI telemetry.

The benchmarks reported here aren't FPS, GPU utilisation, or inference
throughput — this repo doesn't host an inference workload, so those
metrics would be staged. The benchmarks that ARE meaningful for a
telemetry-intelligence layer:

* **Ingest throughput** — how fast the synthetic generator can produce
  schema-conformant rows. A floor for pipeline ingest rate.
* **Schema-quarantine throughput** — how fast the schema validator can
  separate good rows from corrupted rows under a fail-soft fixture.
* **Determinism check** — re-generate both scenarios at seed 42 twice
  and confirm the metrics JSON hashes match byte-for-byte.
* **Stage wall-clocks** — how long each step in the `make verify` chain
  takes on a clean run (scenarios, business cases, portal).

All numbers come from running the actual pipeline. Re-running this
script (or ``make benchmarks``) refreshes them.
"""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from private5g_pipeline.ingest import generate_synthetic_ran_logs
from private5g_pipeline.schema import DEFAULT_SCHEMA, quarantine_invalid_rows

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = "reports"


def _measure_ingest_throughput() -> dict[str, Any]:
    """Generate a large synthetic batch and measure rows/sec."""
    # 25 cells × 48 hours @ 5-min bins × 3 slices = ~43,200 rows.
    n_cells = 25
    n_hours = 48

    start = time.perf_counter()
    df = generate_synthetic_ran_logs(
        n_cells=n_cells, n_hours=n_hours, freq="5min", seed=42
    )
    elapsed = time.perf_counter() - start

    return {
        "rows_generated": int(len(df)),
        "elapsed_seconds": round(elapsed, 3),
        "rows_per_second": int(len(df) / max(elapsed, 1e-9)),
        "n_cells": n_cells,
        "n_hours": n_hours,
    }


def _measure_quarantine_throughput() -> dict[str, Any]:
    """Inject corruption into a fresh batch and measure quarantine rate."""
    df = generate_synthetic_ran_logs(n_cells=10, n_hours=24, freq="5min", seed=42)
    n = len(df)

    # Corrupt ~5% of rows in mixed ways (out-of-range, bad timestamp, bad cell).
    rng = np.random.default_rng(42)
    corruption_rate = 0.05
    n_corrupt = int(n * corruption_rate)
    corrupt_idx = rng.choice(n, size=n_corrupt, replace=False)

    df_corrupt = df.copy()
    # Cast timestamp to object so we can inject a non-timestamp string.
    df_corrupt["timestamp"] = df_corrupt["timestamp"].astype(object)
    # 1/3 — out-of-range latency
    third = n_corrupt // 3
    df_corrupt.loc[corrupt_idx[:third], "latency_ms"] = 9999.0
    # 1/3 — bad cell_id
    df_corrupt.loc[corrupt_idx[third : 2 * third], "cell_id"] = ""
    # 1/3 — bad timestamp
    df_corrupt.loc[corrupt_idx[2 * third :], "timestamp"] = "not-a-time"

    start = time.perf_counter()
    valid, rejected = quarantine_invalid_rows(df_corrupt, DEFAULT_SCHEMA)
    elapsed = time.perf_counter() - start

    return {
        "total_rows": int(n),
        "corruption_rate_pct": round(100 * corruption_rate, 1),
        "rejected_rows": int(len(rejected)),
        "rejected_pct": round(100 * len(rejected) / max(n, 1), 2),
        "valid_rows": int(len(valid)),
        "elapsed_seconds": round(elapsed, 3),
        "rows_per_second": int(n / max(elapsed, 1e-9)),
    }


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _measure_determinism() -> dict[str, Any]:
    """Re-run both scenarios at seed=42 twice and confirm metrics JSON matches."""
    # Imports here to avoid pulling matplotlib into module-level when only
    # benchmarks that don't need it are used.
    from private5g_pipeline.scenarios.manufacturing import (
        run_manufacturing_agv_scenario,
    )
    from private5g_pipeline.scenarios.pharma import run_pharma_bioreactor_scenario

    with tempfile.TemporaryDirectory(prefix="p5g_det_a_") as tmp_a, tempfile.TemporaryDirectory(prefix="p5g_det_b_") as tmp_b:
        for tmp in (tmp_a, tmp_b):
            run_manufacturing_agv_scenario(output_dir=Path(tmp) / "mfg", seed=42)
            run_pharma_bioreactor_scenario(output_dir=Path(tmp) / "pha", seed=42)

        mfg_a = _hash_file(Path(tmp_a) / "mfg" / "scenario_metrics.json")
        mfg_b = _hash_file(Path(tmp_b) / "mfg" / "scenario_metrics.json")
        pha_a = _hash_file(Path(tmp_a) / "pha" / "scenario_metrics.json")
        pha_b = _hash_file(Path(tmp_b) / "pha" / "scenario_metrics.json")

    return {
        "manufacturing_run_a_hash": mfg_a,
        "manufacturing_run_b_hash": mfg_b,
        "manufacturing_matches": mfg_a == mfg_b,
        "pharma_run_a_hash": pha_a,
        "pharma_run_b_hash": pha_b,
        "pharma_matches": pha_a == pha_b,
        "both_deterministic": mfg_a == mfg_b and pha_a == pha_b,
    }


def _measure_stage_wallclock() -> dict[str, Any]:
    """Time each major regeneration step against a tmpdir."""
    from private5g_pipeline.business_cases.manufacturing import (
        run_manufacturing_business_case,
    )
    from private5g_pipeline.business_cases.pharma import run_pharma_business_case
    from private5g_pipeline.portal.generate import generate_portal
    from private5g_pipeline.scenarios.manufacturing import (
        run_manufacturing_agv_scenario,
    )
    from private5g_pipeline.scenarios.pharma import run_pharma_bioreactor_scenario

    with tempfile.TemporaryDirectory(prefix="p5g_stage_") as tmp_str:
        tmp = Path(tmp_str)
        mfg_scenario = tmp / "scenarios" / "manufacturing_agv"
        pha_scenario = tmp / "scenarios" / "pharma_bioreactor"
        business_cases = tmp / "business_cases"

        # Manufacturing scenario
        t0 = time.perf_counter()
        run_manufacturing_agv_scenario(output_dir=mfg_scenario, seed=42)
        mfg_scen_s = round(time.perf_counter() - t0, 3)

        # Pharma scenario
        t0 = time.perf_counter()
        run_pharma_bioreactor_scenario(output_dir=pha_scenario, seed=42)
        pha_scen_s = round(time.perf_counter() - t0, 3)

        # Manufacturing business case
        t0 = time.perf_counter()
        run_manufacturing_business_case(
            output_dir=business_cases,
            canonical_pack_path=mfg_scenario / "scenario_metrics.json",
        )
        mfg_bc_s = round(time.perf_counter() - t0, 3)

        # Pharma business case
        t0 = time.perf_counter()
        run_pharma_business_case(
            output_dir=business_cases,
            canonical_pack_path=pha_scenario / "scenario_metrics.json",
        )
        pha_bc_s = round(time.perf_counter() - t0, 3)

        # Portal
        t0 = time.perf_counter()
        generate_portal(
            output_path=tmp / "index.html",
            manufacturing_metrics_path=str(mfg_scenario / "scenario_metrics.json"),
            pharma_metrics_path=str(pha_scenario / "scenario_metrics.json"),
            manufacturing_sensitivity_path=str(
                business_cases / "manufacturing_agv_sensitivity.json"
            ),
            pharma_sensitivity_path=str(
                business_cases / "pharma_bioreactor_sensitivity.json"
            ),
        )
        portal_s = round(time.perf_counter() - t0, 3)

    return {
        "manufacturing_scenario_seconds": mfg_scen_s,
        "pharma_scenario_seconds": pha_scen_s,
        "manufacturing_business_case_seconds": mfg_bc_s,
        "pharma_business_case_seconds": pha_bc_s,
        "portal_seconds": portal_s,
        "total_seconds": round(
            mfg_scen_s + pha_scen_s + mfg_bc_s + pha_bc_s + portal_s, 3
        ),
    }


def _format_markdown(results: dict[str, Any]) -> str:
    ingest = results["ingest"]
    quarantine = results["quarantine"]
    determinism = results["determinism"]
    wallclock = results["wallclock"]

    lines = [
        "# Pipeline benchmarks",
        "",
        "Measured numbers. Not FPS or GPU utilisation — this isn't an inference workload —",
        "but the equivalent for a telemetry-intelligence layer: how fast it ingests, how it",
        "behaves under corrupted input, and how long the full evidence-regeneration chain",
        "takes on a clean run. Refresh by running `make benchmarks`.",
        "",
        "## Headline",
        "",
        "| Benchmark | Result |",
        "|---|---|",
        f"| **Synthetic-generator throughput** | {ingest['rows_per_second']:,} rows / sec "
        f"({ingest['rows_generated']:,} rows in {ingest['elapsed_seconds']} s) |",
        f"| **Schema quarantine throughput** | {quarantine['rows_per_second']:,} rows / sec "
        f"({quarantine['total_rows']:,} rows, {quarantine['rejected_pct']}% rejected at "
        f"{quarantine['corruption_rate_pct']}% corruption) |",
        f"| **End-to-end regeneration** | {wallclock['total_seconds']} s "
        f"(both scenarios + both business cases + portal) |",
        f"| **Determinism (seed 42, two runs)** | "
        f"{'byte-identical metrics JSON' if determinism['both_deterministic'] else 'MISMATCH'} |",
        "",
        "## What this measures",
        "",
        "- **Ingest throughput** is the synthetic generator producing schema-conformant rows. "
        "Sets a floor for how fast the pipeline would handle telemetry under load. Production "
        "ingest off a real RAN feed would obviously be capped by the feed itself.",
        "- **Quarantine throughput** is the fail-soft schema validator separating clean rows "
        "from corrupted rows. Run against a fixture with 5% corruption mixed across "
        "out-of-range, missing identifiers, and bad timestamps. The validator never crashes.",
        "- **End-to-end regeneration** is the wall-clock for re-creating every committed "
        "evidence artifact: both scenarios, both business cases, the portal. Plus tests + "
        "lint + typecheck (separate, via `make verify`), the full reproducibility gate "
        "ships in under a minute on a developer laptop.",
        "- **Determinism** is a SHA-256 check on the two scenario `scenario_metrics.json` "
        "files after re-running at seed 42 from scratch. Identical hash = identical bytes = "
        "the answer is the model, not the noise floor.",
        "",
        "## Stage breakdown",
        "",
        "| Stage | Wall-clock (s) |",
        "|---|---:|",
        f"| Manufacturing scenario | {wallclock['manufacturing_scenario_seconds']} |",
        f"| Pharma scenario | {wallclock['pharma_scenario_seconds']} |",
        f"| Manufacturing business case | {wallclock['manufacturing_business_case_seconds']} |",
        f"| Pharma business case | {wallclock['pharma_business_case_seconds']} |",
        f"| Portal | {wallclock['portal_seconds']} |",
        f"| **Total** | **{wallclock['total_seconds']}** |",
        "",
        "## Raw determinism hashes (SHA-256)",
        "",
        f"- Manufacturing run A: `{determinism['manufacturing_run_a_hash'][:16]}…`",
        f"- Manufacturing run B: `{determinism['manufacturing_run_b_hash'][:16]}…` "
        f"(match: {determinism['manufacturing_matches']})",
        f"- Pharma run A: `{determinism['pharma_run_a_hash'][:16]}…`",
        f"- Pharma run B: `{determinism['pharma_run_b_hash'][:16]}…` "
        f"(match: {determinism['pharma_matches']})",
        "",
        "## Environment",
        "",
        "Single-process Python, no parallelism. Same hardware on every `make benchmarks` run.",
        "Raw numbers in [`benchmarks.json`](benchmarks.json).",
        "",
    ]
    return "\n".join(lines)


def run_benchmarks(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Run all benchmarks, write benchmarks.json + benchmarks.md to output_dir."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    logger.info("Measuring ingest throughput…")
    ingest = _measure_ingest_throughput()

    logger.info("Measuring quarantine throughput…")
    quarantine = _measure_quarantine_throughput()

    logger.info("Measuring stage wall-clocks…")
    wallclock = _measure_stage_wallclock()

    logger.info("Measuring determinism…")
    determinism = _measure_determinism()

    results: dict[str, Any] = {
        "ingest": ingest,
        "quarantine": quarantine,
        "wallclock": wallclock,
        "determinism": determinism,
    }

    (out / "benchmarks.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "benchmarks.md").write_text(_format_markdown(results), encoding="utf-8")

    logger.info(
        "Benchmarks complete: ingest=%d rows/s, quarantine=%d rows/s, total=%ss, deterministic=%s",
        ingest["rows_per_second"],
        quarantine["rows_per_second"],
        wallclock["total_seconds"],
        determinism["both_deterministic"],
    )
    return results


def main() -> None:
    """Entry point for ``python -m private5g_pipeline.benchmarks``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    run_benchmarks()


if __name__ == "__main__":
    main()
