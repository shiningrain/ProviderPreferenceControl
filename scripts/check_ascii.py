#!/usr/bin/env python3
"""Check that release files contain ASCII text only."""

from __future__ import annotations

import argparse
from pathlib import Path


SKIP_SUFFIXES = {
    ".bin",
    ".cache",
    ".gif",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".pkl",
    ".png",
    ".pt",
    ".safetensors",
    ".zip",
}


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".git") for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.root)
    failures = []
    for path in iter_files(root):
        data = path.read_bytes()
        try:
            data.decode("ascii")
        except UnicodeDecodeError as exc:
            failures.append((path, exc.start + 1))

    if failures:
        for path, offset in failures:
            print(f"non-ascii: {path}:{offset}")
        return 1

    print(f"ascii-ok: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
