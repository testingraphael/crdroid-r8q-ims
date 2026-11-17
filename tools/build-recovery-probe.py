#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Package the read-only recovery metadata diagnostic as an unsigned sideload ZIP."""

import argparse
import hashlib
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()
if args.output.exists():
    parser.error("Choose a new output file")
script = Path(__file__).with_name("recovery-read-super.sh").read_bytes()
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    entry = zipfile.ZipInfo("META-INF/com/google/android/update-binary", (1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.external_attr = 0o100755 << 16
    archive.writestr(entry, script)
print("Unsigned read-only diagnostic:", args.output)
print("SHA-256:", hashlib.sha256(args.output.read_bytes()).hexdigest())
