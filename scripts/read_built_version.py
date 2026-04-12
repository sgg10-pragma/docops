#!/usr/bin/env python3
"""Print the version embedded in the built wikiops wheel filename."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read the version from a built wheel in a dist directory."
    )
    parser.add_argument(
        "--dist-dir",
        default="dist",
        help="Directory containing built wheel artifacts.",
    )
    parser.add_argument(
        "--distribution",
        default="wikiops",
        help="Distribution name to match in wheel filenames.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dist_dir = Path(args.dist_dir)
    if not dist_dir.exists():
        raise FileNotFoundError(f"Missing dist directory: {dist_dir}")

    wheels = sorted(dist_dir.glob(f"{args.distribution}-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            f"Expected exactly one wheel for {args.distribution!r} in {dist_dir}, "
            f"found {len(wheels)}."
        )

    pattern = re.compile(
        rf"^{re.escape(args.distribution)}-(?P<version>.+?)-[^-]+-[^-]+-[^-]+\.whl$"
    )
    match = pattern.match(wheels[0].name)
    if match is None:
        raise RuntimeError(f"Could not parse version from wheel name: {wheels[0].name}")

    print(match.group("version"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
