"""Tests for private5g_pipeline.cli argument parsing and entry-point behaviour."""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from private5g_pipeline.cli import parse_args

# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


def _parse(*args: str) -> object:
    with patch.object(sys, "argv", ["cli", *args]):
        return parse_args()


def test_parse_generate_synthetic_flag():
    ns = _parse("--generate_synthetic")
    assert ns.generate_synthetic is True
    assert ns.input_dir is None


def test_parse_input_dir():
    ns = _parse("--input_dir", "/some/path")
    assert ns.input_dir == "/some/path"
    assert ns.generate_synthetic is False


def test_parse_config_path():
    ns = _parse("--config", "configs/pipeline_config.yaml")
    assert ns.config == "configs/pipeline_config.yaml"


def test_parse_partition_by_date_cell():
    ns = _parse("--generate_synthetic", "--partition_by_date_cell")
    assert ns.partition_by_date_cell is True


def test_parse_allow_schema_errors():
    ns = _parse("--generate_synthetic", "--allow_schema_errors")
    assert ns.allow_schema_errors is True


def test_parse_output_parquet():
    ns = _parse("--generate_synthetic", "--output_parquet", "out/test.parquet")
    assert ns.output_parquet == "out/test.parquet"


# ---------------------------------------------------------------------------
# main() guard: no args → SystemExit
# ---------------------------------------------------------------------------


def test_main_no_args_raises_system_exit():
    """Running with no actionable flag must exit rather than hang or crash."""
    from private5g_pipeline.cli import main

    with patch.object(sys, "argv", ["cli"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    # The message should be a non-zero exit (string message counts as truthy)
    assert exc_info.value.code


# ---------------------------------------------------------------------------
# main() end-to-end with synthetic flag (smoke)
# ---------------------------------------------------------------------------


def test_main_synthetic_runs(tmp_path):
    """main() with --generate_synthetic should produce a Parquet file."""
    import pandas as pd

    from private5g_pipeline.cli import main

    out = tmp_path / "out.parquet"
    with patch.object(
        sys,
        "argv",
        ["cli", "--generate_synthetic", "--output_parquet", str(out)],
    ):
        main()

    assert out.exists()
    df = pd.read_parquet(str(out))
    assert len(df) > 0
