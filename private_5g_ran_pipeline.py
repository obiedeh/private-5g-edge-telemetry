#!/usr/bin/env python3
"""Thin CLI wrapper around ``private5g_pipeline.cli``.

Kept for backwards compatibility with documentation / scripts that invoke
``python private_5g_ran_pipeline.py ...``. New work should prefer
``python -m private5g_pipeline``, which uses the same entry point.
"""

from __future__ import annotations

from private5g_pipeline.cli import main

if __name__ == "__main__":
    main()
