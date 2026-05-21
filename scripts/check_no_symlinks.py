#!/usr/bin/env python3
"""Fail if the artifact contains symbolic links."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.root)
    links = sorted(path for path in root.rglob("*") if path.is_symlink())
    if links:
        for path in links:
            print(f"symlink-found: {path}")
        return 1
    print(f"no-symlinks-ok: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
