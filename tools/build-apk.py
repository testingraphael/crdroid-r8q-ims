#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Build and sign the local PhhIms release and record its inputs."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_digest(source):
    excluded = (".git/", ".gradle/", "build/", "app/build/", "app/.cxx/")
    digest = hashlib.sha256()
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        if relative == "local.properties" or relative.startswith(excluded):
            continue
        digest.update(relative.encode() + b"\0" + bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".build.json").exists():
        parser.error("Choose a new output and preserve the prior build")
    source, sdk = args.source.resolve(), args.sdk.resolve()
    java = subprocess.run(["java", "-version"], check=True, capture_output=True, text=True)
    if not re.search(r'version "17\.', java.stderr + java.stdout):
        parser.error("This build requires JDK 17")
    lock = json.loads((ROOT / "source-lock.json").read_text())
    for relative, expected in lock["patch_sha256"].items():
        if sha256(ROOT / relative) != expected:
            parser.error("Locked patch changed: " + relative)
    service = (source / "app/src/main/java/me/phh/ims/PhhImsService.kt").read_text()
    if "overrideConfig" in service or "ensureVolteCarrierConfig" in service:
        parser.error("The source still contains the excluded carrier override")
    tree_hash = source_digest(source)
    env = {**os.environ, "ANDROID_HOME": str(sdk), "ANDROID_SDK_ROOT": str(sdk)}
    subprocess.run(["./gradlew", "--no-daemon", "--console=plain", ":app:assembleRelease"],
                   cwd=source, env=env, check=True)
    if source_digest(source) != tree_hash:
        raise RuntimeError("Source inputs changed during compilation")
    unsigned = source / "app/build/outputs/apk/release/app-release-unsigned.apk"
    tools = sdk / "build-tools/35.0.0"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="phhims-sign-") as temp:
        aligned = Path(temp) / "aligned.apk"
        subprocess.run([str(tools / "zipalign"), "-p", "-f", "4", str(unsigned), str(aligned)], check=True)
        subprocess.run([str(tools / "apksigner"), "sign", "--ks", str(args.keystore.resolve()),
                        "--ks-pass", "file:" + str(args.password_file.resolve()),
                        "--v4-signing-enabled", "false", "--out", str(args.output.resolve()),
                        str(aligned)], check=True)
    cert = subprocess.run([str(tools / "apksigner"), "verify", "--print-certs",
                           str(args.output.resolve())], check=True, capture_output=True, text=True).stdout
    signer = re.search(r"Signer #1 certificate SHA-256 digest: ([0-9a-f]+)", cert)
    if not signer:
        raise RuntimeError("Signing certificate digest is unavailable")
    receipt = {
        "apk_sha256": sha256(args.output), "apk_signer_sha256": signer[1],
        "source_tree_sha256": tree_hash,
        "source_tree_hash_method": "Sorted relative path, NUL, binary SHA-256 per file; excludes Gradle outputs, .git and local.properties",
        "source_lock_sha256": sha256(ROOT / "source-lock.json"),
        "java": (java.stderr + java.stdout).splitlines()[0],
        "gradle": "8.5", "agp": "8.2.0", "kotlin": "1.8.10", "sdk_platform": 33,
        "build_tools": "35.0.0", "ndk": "25.1.8937393", "cmake": "3.22.1", "abi": "arm64-v8a",
        "build_result": "assembleRelease passed; zipalign and APK signature verification passed",
        "provenance_limit": "Local build record, not an independent signed attestation of source provenance"
    }
    args.output.with_suffix(".build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
