#!/usr/bin/env python3
"""Compatibility entry point for the repository-local pipeline preflight."""

from __future__ import annotations

import sys

from pipeline import main


if __name__ == "__main__":
    raise SystemExit(main(["preflight", *sys.argv[1:]]))
