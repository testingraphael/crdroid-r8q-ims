#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check the release files against the manifest committed with the source."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest_bytes = (root / "release-manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    expected = {}
    for asset in manifest["assets"]:
        name = asset["file"]
        if not re.fullmatch(r"[A-Za-z0-9._-]+", name) or name in expected:
            raise SystemExit("Invalid or duplicate asset name")
        if not re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]):
            raise SystemExit(f"Invalid SHA-256 for {name}")
        if type(asset["bytes"]) is not int or not 0 < asset["bytes"] < 2**31:
            raise SystemExit(f"Invalid release size for {name}")
        expected[name] = asset
    checksums = (root / "SHA256SUMS").read_bytes()
    wanted = "".join(
        f"{asset['sha256']}  {name}\n" for name, asset in sorted(expected.items())
    ).encode()
    if checksums != wanted:
        raise SystemExit("SHA256SUMS differs from the committed manifest")
    if args.directory is None:
        print("Release metadata OK")
        return
    directory = args.directory
    names = set(expected) | {"SHA256SUMS", "release-manifest.json"}
    if {p.name for p in directory.iterdir()} != names:
        raise SystemExit("Release directory has missing or unexpected files")
    for name, content in (
        ("SHA256SUMS", checksums), ("release-manifest.json", manifest_bytes)
    ):
        path = directory / name
        if path.is_symlink() or path.read_bytes() != content:
            raise SystemExit(f"Release metadata mismatch: {name}")
    for name, asset in expected.items():
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"Invalid asset: {name}")
        if path.stat().st_size != asset["bytes"]:
            raise SystemExit(f"Size mismatch: {name}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != asset["sha256"]:
            raise SystemExit(f"SHA-256 mismatch: {name}")
        print(f"OK {name}")


if __name__ == "__main__":
    main()
