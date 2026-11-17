#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Resize AVB image padding without changing its payload or vbmeta block."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess


def footer(data):
    fields = struct.unpack_from(">4sIIQQQ28s", data, len(data) - 64)
    if fields[0] != b"AVBf":
        raise ValueError("Image has no AVB footer")
    return fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--partition-size", type=int, required=True)
    parser.add_argument("--avbtool", type=Path, required=True)
    args = parser.parse_args()
    original = args.input.read_bytes()
    if hashlib.sha256(original).hexdigest() != args.input_sha256:
        parser.error("Input image differs from the verified ROM archive")
    if args.output.exists() or args.output.resolve() == args.input.resolve():
        parser.error("Choose a new output file and preserve the original image")
    before = footer(original)
    image_size, offset, size = before[3:6]
    if args.partition_size % 4096 or offset + size + 4096 > args.partition_size:
        parser.error("Payload and AVB metadata do not fit the supplied partition capacity")
    if any(original[offset + size:len(original) - 64]):
        parser.error("Unexpected nonzero data exists beyond the AVB metadata")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.input, args.output)
    subprocess.run(["python3", str(args.avbtool), "resize_image", "--image", str(args.output),
                    "--partition_size", str(args.partition_size)], check=True)
    changed = args.output.read_bytes()
    after = footer(changed)
    if len(changed) != args.partition_size or after != before:
        raise RuntimeError("Image size or preserved AVB footer fields differ")
    if changed[:image_size] != original[:image_size]:
        raise RuntimeError("Image payload changed")
    if changed[offset:offset + size] != original[offset:offset + size]:
        raise RuntimeError("Existing vbmeta bytes changed")
    subprocess.run(["python3", str(args.avbtool), "verify_image", "--image", str(args.output)], check=True)
    record = {"input_sha256": args.input_sha256,
              "output_sha256": hashlib.sha256(changed).hexdigest(),
              "partition_size": args.partition_size,
              "original_payload_size": image_size,
              "payload_sha256": hashlib.sha256(original[:image_size]).hexdigest(),
              "vbmeta_sha256": hashlib.sha256(original[offset:offset + size]).hexdigest(),
              "payload_unchanged": True, "vbmeta_unchanged": True}
    args.output.with_suffix(".verification.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
