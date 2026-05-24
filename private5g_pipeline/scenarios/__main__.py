"""CLI: ``python -m private5g_pipeline.scenarios --vertical manufacturing|pharma``.

Runs one vertical scenario and writes its evidence pack to
``reports/scenarios/<vertical>/``.
"""

from __future__ import annotations

import argparse
import logging

from private5g_pipeline.scenarios.manufacturing import (
    DEFAULT_LATENCY_BUDGET_MS,
    DEFAULT_OUTPUT_DIR as MFG_OUT,
    run_manufacturing_agv_scenario,
)
from private5g_pipeline.scenarios.pharma import (
    DEFAULT_DETECTION_THRESHOLD,
    DEFAULT_OUTPUT_DIR as PHA_OUT,
    run_pharma_bioreactor_scenario,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a vertical scenario evidence pack.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--vertical",
        choices=("manufacturing", "pharma", "all"),
        required=True,
        help="Which vertical scenario to run.",
    )
    parser.add_argument(
        "--output_dir",
        default=None,
        help="Override the evidence-pack output directory.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="RNG seed for the synthetic telemetry generator.",
    )
    parser.add_argument(
        "--latency_budget_ms",
        type=float,
        default=DEFAULT_LATENCY_BUDGET_MS,
        help="Manufacturing only: AGV control-loop latency budget.",
    )
    parser.add_argument(
        "--detection_threshold",
        type=float,
        default=DEFAULT_DETECTION_THRESHOLD,
        help="Pharma only: default z-score detection threshold.",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    args = _build_parser().parse_args()

    if args.vertical in ("manufacturing", "all"):
        out = (
            args.output_dir
            if (args.vertical == "manufacturing" and args.output_dir)
            else MFG_OUT
        )
        run_manufacturing_agv_scenario(
            output_dir=out,
            latency_budget_ms=args.latency_budget_ms,
            seed=args.seed,
        )

    if args.vertical in ("pharma", "all"):
        out = (
            args.output_dir
            if (args.vertical == "pharma" and args.output_dir)
            else PHA_OUT
        )
        run_pharma_bioreactor_scenario(
            output_dir=out,
            default_threshold=args.detection_threshold,
            seed=args.seed,
        )


if __name__ == "__main__":
    main()
