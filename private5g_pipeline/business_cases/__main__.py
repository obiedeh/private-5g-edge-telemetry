"""CLI: ``python -m private5g_pipeline.business_cases --case manufacturing|pharma|all``.

Generates the one-page Markdown business-case report for the selected
vertical, reading the headline answer from the canonical scenario
evidence pack and adding a sensitivity table.
"""

from __future__ import annotations

import argparse
import logging

from private5g_pipeline.business_cases.manufacturing import (
    DEFAULT_OUTPUT_DIR as MFG_OUT,
)
from private5g_pipeline.business_cases.manufacturing import (
    run_manufacturing_business_case,
)
from private5g_pipeline.business_cases.pharma import (
    DEFAULT_OUTPUT_DIR as PHA_OUT,
)
from private5g_pipeline.business_cases.pharma import (
    run_pharma_business_case,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a vertical business-case Markdown report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--case",
        choices=("manufacturing", "pharma", "all"),
        required=True,
        help="Which business case to generate.",
    )
    parser.add_argument(
        "--output_dir",
        default=None,
        help="Override the business-case output directory.",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    args = _build_parser().parse_args()

    if args.case in ("manufacturing", "all"):
        out = (
            args.output_dir
            if (args.case == "manufacturing" and args.output_dir)
            else MFG_OUT
        )
        run_manufacturing_business_case(output_dir=out)

    if args.case in ("pharma", "all"):
        out = (
            args.output_dir
            if (args.case == "pharma" and args.output_dir)
            else PHA_OUT
        )
        run_pharma_business_case(output_dir=out)


if __name__ == "__main__":
    main()
