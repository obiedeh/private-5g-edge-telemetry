from __future__ import annotations

import argparse
import logging

from private5g_pipeline.config import PipelineConfig, load_config
from private5g_pipeline.pipeline import run_pipeline_config

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulation-first private 5G telemetry pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", default=None, help="YAML pipeline config.")
    parser.add_argument("--input_dir", default=None, help="Directory containing raw CSV telemetry.")
    parser.add_argument("--output_parquet", default=None, help="Output Parquet path.")
    parser.add_argument("--generate_synthetic", action="store_true", help="Generate synthetic telemetry.")
    parser.add_argument("--partition_by_date_cell", action="store_true", help="Partition Parquet by date/cell_id.")
    parser.add_argument("--allow_schema_errors", action="store_true", help="Quarantine invalid rows and continue.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    args = parse_args()
    config = load_config(args.config) if args.config else PipelineConfig()

    if args.input_dir:
        config.ingestion.mode = "csv"
        config.ingestion.input_dir = args.input_dir
    if args.generate_synthetic:
        config.ingestion.mode = "synthetic"
    if args.output_parquet:
        config.export.output_parquet = args.output_parquet
    if args.partition_by_date_cell:
        config.export.partition_cols = ["date", "cell_id"]
    if args.allow_schema_errors:
        config.transform.fail_on_schema_error = False

    if not args.config and not args.generate_synthetic and not args.input_dir:
        raise SystemExit("Error: provide --config, --input_dir, or --generate_synthetic.")

    run_pipeline_config(config)


if __name__ == "__main__":
    main()
