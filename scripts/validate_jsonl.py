#!/usr/bin/env python3
"""Validate that a JSONL file can be parsed line by line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    count = 0
    with path.open("r", encoding="ascii") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            json.loads(line)
            count += 1

    print(f"jsonl-ok: {path} records={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
