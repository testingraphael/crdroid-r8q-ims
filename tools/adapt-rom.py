#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Prepare a separate r8q OTA copy for the measured SM-G781B partition sizes."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile

ROM_HASH = "122f4bd79ea755ba9a72ec3fdd4b59fbd12a878624743b973eae08e8bd646198"
EMPTY_HASH = "1ba50b964ac6d8eefa5009456f358d530805658142cc921eec8bcf24c79792e3"
ROOT = Path(__file__).resolve().parent.parent


def digest_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def geometry(image):
    if struct.unpack_from("<I", image)[0] != 0x616C4467:
        raise ValueError("Expected a raw liblp metadata image")
    header = 4096
    if struct.unpack_from("<I", image, header)[0] != 0x414C5030:
        raise ValueError("Missing liblp metadata header")
    header_size = struct.unpack_from("<I", image, header + 8)[0]
    offset, count, entry_size = struct.unpack_from("<III", image, header + 116)
    if count != 1 or entry_size != 64:
        raise ValueError("This adapter only supports the verified single-device super layout")
    block = header + header_size + offset
    first_sector, alignment, alignment_offset, device_size = struct.unpack_from("<QIIQ", image, block)
    return first_sector * 512, alignment, alignment_offset, device_size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pit", type=Path, required=True)
    parser.add_argument("--samloader", type=Path, required=True)
    parser.add_argument("--avbtool", type=Path, required=True)
    parser.add_argument("--super-empty", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.input.resolve():
        parser.error("Preserve the original ZIP and choose a new output path")
    if digest_file(args.input) != ROM_HASH or digest_file(args.super_empty) != EMPTY_HASH:
        parser.error("Input archive or official super metadata hash mismatch")
    pit = subprocess.run([str(args.samloader), "print-pit", "--file", str(args.pit)],
                         check=True, capture_output=True, text=True).stdout
    partitions = {}
    for block in pit.split("--- Entry #"):
        name = re.search(r"^Partition Name: (\S+)$", block, re.M)
        count = re.search(r"^Partition Block Count: (\d+)$", block, re.M)
        kind = re.search(r"^Device Type: 8 \(UFS\)$", block, re.M)
        if name and count and kind:
            partitions[name[1]] = int(count[1]) * 4096
    expected = {"BOOT": 67108864, "DTBO": 10485760, "RECOVERY": 82694144,
                "SUPER": 10292822016, "VBMETA": 65536}
    if any(partitions.get(name) != size for name, size in expected.items()):
        parser.error("PIT does not match the inspected SM-G781B layout")
    first, alignment, alignment_offset, size = geometry(args.super_empty.read_bytes())
    if size != partitions["SUPER"] or alignment != 1048576 or alignment_offset != 0:
        parser.error("Official super metadata differs from measured geometry")
    group_limit = size - 4 * 1024 * 1024
    changed_names = {"boot.img", "dtbo.img", "dynamic_partitions_op_list", "unsparse_super_empty.img"}
    with zipfile.ZipFile(args.input) as original, tempfile.TemporaryDirectory(prefix="r8q-fit-") as temp:
        stage = Path(temp)
        replacements = {"unsparse_super_empty.img": args.super_empty}
        for name, partition in (("boot.img", "BOOT"), ("dtbo.img", "DTBO")):
            source = stage / ("original-" + name)
            source.write_bytes(original.read(name))
            target = stage / name
            subprocess.run(["python3", str(ROOT / "tools/fit-image-padding.py"),
                            "--input", str(source), "--output", str(target),
                            "--input-sha256", digest_file(source),
                            "--partition-size", str(partitions[partition]),
                            "--avbtool", str(args.avbtool)], check=True)
            replacements[name] = target
        operations = original.read("dynamic_partitions_op_list").decode()
        if operations.count("10638852096") != 2:
            raise ValueError("Unexpected original dynamic-partition operation list")
        operations = operations.replace("10638852096", str(group_limit))
        sizes = [(name, int(length)) for name, length in re.findall(r"^resize (\S+) (\d+)$", operations, re.M)]
        if len(sizes) != 5 or sum(length for _, length in sizes) > group_limit:
            raise ValueError("Logical image allocations exceed the target group")
        cursor = first
        layout = []
        for name, length in sizes:
            cursor = ((cursor + alignment - 1) // alignment) * alignment
            if length % 512 or cursor + length > size:
                raise ValueError("Aligned logical image allocations exceed physical super")
            layout.append({"partition": name, "start": cursor, "length": length})
            cursor += length
        op_file = stage / "dynamic_partitions_op_list"
        op_file.write_text(operations)
        replacements[op_file.name] = op_file
        hashes = {}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w", allowZip64=True) as adapted:
            for info in original.infolist():
                entry = copy.copy(info)
                if info.filename in replacements:
                    data = replacements[info.filename].read_bytes()
                    entry.file_size = len(data)
                    adapted.writestr(entry, data)
                else:
                    h = hashlib.sha256()
                    with original.open(info) as source, adapted.open(entry, "w") as target:
                        while chunk := source.read(8 * 1024 * 1024):
                            h.update(chunk)
                            target.write(chunk)
                    hashes[info.filename] = h.hexdigest()
        with zipfile.ZipFile(args.output) as adapted:
            if adapted.testzip() is not None:
                raise ValueError("Adapted ZIP failed its CRC check")
            for name, expected_hash in hashes.items():
                with adapted.open(name) as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != expected_hash:
                        raise ValueError("An unrelated OTA entry changed: " + name)
        record = {"source_zip_sha256": ROM_HASH, "adapted_zip_sha256": digest_file(args.output),
                  "changed_entries": sorted(changed_names), "unrelated_entries_unchanged": True,
                  "super_empty_sha256": EMPTY_HASH, "physical_super_bytes": size,
                  "group_limit": group_limit, "aligned_feasibility_layout": layout,
                  "whole_file_signature": "Removed by local repack; not an upstream signed release",
                  "allocation_check": "One-device aligned feasibility calculation, not execution of the updater"}
        args.output.with_suffix(".verification.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
