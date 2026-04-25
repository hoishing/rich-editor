#!/usr/bin/env -S uv run --project . python
"""Compatibility runner for the Textual Pilot end-to-end suite."""

from __future__ import annotations

import asyncio

from tests.runner import main


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
