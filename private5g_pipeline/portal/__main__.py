"""CLI: ``python -m private5g_pipeline.portal``.

Renders ``reports/index.html`` (cards view) and/or ``reports/dashboard.html``
(executive-technical dashboard) from the committed evidence packs.
"""

from __future__ import annotations

import argparse
import logging

from private5g_pipeline.portal.dashboard import (
    DEFAULT_OUTPUT_PATH as DEFAULT_DASHBOARD_PATH,
    generate_dashboard,
)
from private5g_pipeline.portal.generate import (
    DEFAULT_OUTPUT_PATH as DEFAULT_PORTAL_PATH,
    generate_portal,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render the private-5G evidence surfaces.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--target",
        choices=("portal", "dashboard", "both"),
        default="both",
        help="Which surface to render. 'both' writes the cards portal and the "
             "single-page executive dashboard.",
    )
    parser.add_argument(
        "--portal_path",
        default=DEFAULT_PORTAL_PATH,
        help="Where to write the cards-view portal HTML.",
    )
    parser.add_argument(
        "--dashboard_path",
        default=DEFAULT_DASHBOARD_PATH,
        help="Where to write the single-page executive dashboard HTML.",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    args = _build_parser().parse_args()

    if args.target in ("portal", "both"):
        generate_portal(output_path=args.portal_path)

    if args.target in ("dashboard", "both"):
        generate_dashboard(output_path=args.dashboard_path)


if __name__ == "__main__":
    main()
