#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check the r8q recovery metadata capture without accessing a device."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect(blob, report, plan):
    digest = hashlib.sha256(blob).hexdigest()
    require(len(blob) == 1048576 and digest in report, "Capture length or report hash mismatch")
    capacities = dict(re.findall(r"^(boot|recovery|dtbo|super|vbmeta) (\d+)$", report, re.M))
    expected = {"boot": 67108864, "recovery": 82694144, "dtbo": 10485760,
                "super": 10292822016, "vbmeta": 65536}
    require({k: int(v) for k, v in capacities.items()} == expected, "Unexpected block capacities")
    for offset in (4096, 8192):
        geometry = bytearray(blob[offset:offset + 52])
        require(struct.unpack_from("<II", geometry) == (0x616C4467, 52), "Unknown geometry format")
        checksum = geometry[8:40]
        geometry[8:40] = bytes(32)
        require(hashlib.sha256(geometry).digest() == checksum, "Geometry checksum mismatch")
        require(struct.unpack_from("<III", geometry, 40) == (65536, 2, 4096), "Unexpected geometry")
    copies = []
    for copy in range(2):
        for slot in range(2):
            offset = 12288 + (copy * 2 + slot) * 65536
            magic, major, minor, length = struct.unpack_from("<IHHI", blob, offset)
            require(magic == 0x414C5030 and major == 10 and minor <= 2 and length in (128, 256),
                    "Unknown metadata header")
            header = bytearray(blob[offset:offset + length])
            checksum = header[12:44]
            header[12:44] = bytes(32)
            require(hashlib.sha256(header).digest() == checksum, "Header checksum mismatch")
            table_size = struct.unpack_from("<I", header, 44)[0]
            require(length + table_size <= 65536, "Metadata exceeds its slot")
            tables = blob[offset + length:offset + length + table_size]
            require(hashlib.sha256(tables).digest() == header[48:80], "Table checksum mismatch")
            decoded = {}
            for name, position, size in (("partitions", 80, 52), ("extents", 92, 24),
                                         ("groups", 104, 48), ("devices", 116, 64)):
                start, count, entry = struct.unpack_from("<III", header, position)
                require(entry == size and start + count * entry <= table_size, "Invalid table bounds")
                decoded[name] = [tables[start + i * entry:start + (i + 1) * entry] for i in range(count)]
            require(len(decoded["devices"]) == 1, "Expected a single-device super layout")
            device = decoded["devices"][0]
            require(struct.unpack_from("<QIIQ", device) == (2048, 1048576, 0, expected["super"]),
                    "Block device geometry differs from the verified target")
            require(device[24:60].split(b"\0")[0] == b"super", "Unexpected metadata device")
            groups = [{"name": row[:36].split(b"\0")[0].decode("ascii"),
                       "maximum_bytes": struct.unpack_from("<Q", row, 40)[0]} for row in decoded["groups"]]
            partitions, intervals = [], []
            for row in decoded["partitions"]:
                name = row[:36].split(b"\0")[0].decode("ascii")
                attributes, first, count, group = struct.unpack_from("<IIII", row, 36)
                require(group < len(groups) and first + count <= len(decoded["extents"]),
                        "Invalid partition extent or group index")
                size = 0
                for extent in decoded["extents"][first:first + count]:
                    sectors, kind, target, source = struct.unpack("<QIQI", extent)
                    size += sectors * 512
                    if kind == 0:
                        require(source == 0 and target >= 2048 and (target + sectors) * 512 <= expected["super"],
                                "Extent exceeds the physical device")
                        intervals.append((target, target + sectors, name))
                    else:
                        require(kind == 1, "Unsupported extent type")
                require(groups[group]["name"] != "default" or size == 0, "Populated default group")
                partitions.append({"name": name, "group": groups[group]["name"], "bytes": size})
            intervals.sort()
            require(all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])), "Overlapping extents")
            copies.append({"copy": copy, "slot": slot, "checksums": "pass", "groups": groups,
                           "partitions": partitions})
    cursor, total = 1048576, 0
    for row in plan["aligned_feasibility_layout"]:
        cursor = ((cursor + 1048575) // 1048576) * 1048576
        require(row["length"] > 0 and row["length"] % 512 == 0 and cursor == row["start"],
                "Unexpected planned alignment")
        cursor += row["length"]
        total += row["length"]
        require(cursor <= expected["super"], "Planned allocation exceeds super")
    require(total <= expected["super"] - 4194304 and plan["group_limit"] == expected["super"] - 4194304,
            "Planned group exceeds the target limit")
    return {"capture_sha256": digest, "capacities": expected, "metadata_copies": copies,
            "planned_image_bytes": total,
            "result": "Checksum, bounds and aligned feasibility checks pass. This is not updater execution."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--rom-layout", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.capture.read_bytes(), args.report.read_text(), json.loads(args.rom_layout.read_text()))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
