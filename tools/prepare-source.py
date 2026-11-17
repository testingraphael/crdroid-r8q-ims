#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Fetch pinned upstream sources and apply the published trial patches."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import urllib.request

REPO = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New, empty source directory")
    args = parser.parse_args()
    target = args.output.resolve()
    if target.exists():
        parser.error("Output already exists. Choose a new directory to preserve local edits.")
    target.mkdir(parents=True)
    lock = json.loads((REPO / "source-lock.json").read_text())
    for source in lock["sources"]:
        url = "https://codeload.github.com/{repository}/tar.gz/{revision}".format(**source)
        archive = urllib.request.urlopen(url, timeout=60).read()
        base = target / source["destination"]
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            for member in tar.getmembers():
                parts = PurePosixPath(member.name).parts[1:]
                if not member.isfile() or not parts or ".." in parts:
                    continue
                path = base.joinpath(*parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(tar.extractfile(member).read())
                path.chmod(member.mode & 0o777)
        print(source["repository"], source["revision"], flush=True)
    # Stop Git discovering the surrounding documentation repository.
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(target.parent)}
    for relative, digest in sorted(lock["patch_sha256"].items()):
        patch = REPO / relative
        data = patch.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise RuntimeError("Locked source patch changed: " + relative)
        for options in (["--check"], []):
            subprocess.run(["git", "apply", *options, "-"], cwd=target,
                           input=data, env=env, check=True)
        print("Applied", patch.name, flush=True)
    service = target / "app/src/main/java/me/phh/ims/PhhImsService.kt"
    if "overrideConfig" in service.read_text():
        raise RuntimeError("Persistent carrier override remains in the source")
    manifest = (target / "app/src/main/AndroidManifest.xml").read_text()
    if "sharedUserId" in manifest or "protected-broadcast" in manifest:
        raise RuntimeError("Required manifest patches are missing")
    if not (target / "app/src/main/java/me/phh/ims/CompatExt.kt").is_file():
        raise RuntimeError("Required r8q compatibility patch is missing")


if __name__ == "__main__":
    main()
