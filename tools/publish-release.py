#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Publish a verified draft from a clean, merged main checkout using gh."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "testingraphael/crdroid-r8q-ims"


def run(*command):
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def api(path):
    return json.loads(run("gh", "api", f"repos/{REPO}/{path}"))


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def check_draft(release, tag, expected):
    require(release["tag_name"] == tag, "Draft release tag differs from the manifest")
    require(release["draft"], "Release must still be a draft")
    assets = release["assets"]
    require(len(assets) == len(expected) and {a["name"] for a in assets} == set(expected), "Unexpected release assets")
    for asset in assets:
        require(asset["state"] == "uploaded", f"Incomplete upload: {asset['name']}")
        record = expected[asset["name"]]
        require(asset["size"] == record["bytes"], f"Wrong asset size: {asset['name']}")
        require(asset.get("digest") == f"sha256:{record['sha256']}", f"Wrong server digest: {asset['name']}")
    return {a["name"]: a["id"] for a in assets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Publish after every check passes")
    args = parser.parse_args()
    require(run("git", "branch", "--show-current") == "main", "Check out merged main first")
    require(not run("git", "status", "--porcelain"), "Working tree must be clean")
    sha = run("git", "rev-parse", "HEAD")
    require(api("git/ref/heads/main")["object"]["sha"] == sha, "Local main differs from GitHub main")
    pulls = api(f"commits/{sha}/pulls")
    require(any(p["merged_at"] and p["merge_commit_sha"] == sha and p["base"]["ref"] == "main"
                and p["base"]["repo"]["full_name"] == REPO for p in pulls),
            "HEAD must be a pull request merged into this repository's main branch")
    manifest = json.loads((ROOT / "release-manifest.json").read_text())
    tag = manifest["release"]
    require(api(f"git/ref/tags/{tag}")["object"]["sha"] == sha, "Release tag must point to merged HEAD")
    release_id = run("gh", "release", "view", tag, "--repo", REPO,
                     "--json", "databaseId", "--jq", ".databaseId")
    expected = {a["file"]: a for a in manifest["assets"]}
    for name in ("SHA256SUMS", "release-manifest.json"):
        content = (ROOT / name).read_bytes()
        expected[name] = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    asset_ids = check_draft(api(f"releases/{release_id}"), tag, expected)
    with tempfile.TemporaryDirectory(prefix="r8q-release-") as tmp:
        subprocess.run(["gh", "release", "download", tag, "--repo", REPO, "--dir", tmp], cwd=ROOT, check=True)
        subprocess.run([sys.executable, str(ROOT / "tools/verify-release.py"), tmp], cwd=ROOT, check=True)
    if args.publish:
        # Recheck remote state after downloading and address the draft by its ID.
        require(api("git/ref/heads/main")["object"]["sha"] == sha, "GitHub main changed during verification")
        require(api(f"git/ref/tags/{tag}")["object"]["sha"] == sha, "Release tag changed during verification")
        require(check_draft(api(f"releases/{release_id}"), tag, expected) == asset_ids,
                "Draft assets changed during verification")
        subprocess.run(["gh", "api", "--method", "PATCH", f"repos/{REPO}/releases/{release_id}",
                        "-F", "draft=false", "-f", "make_latest=true", "--silent"], cwd=ROOT, check=True)
        print(f"Published https://github.com/{REPO}/releases/tag/{tag}")
    else:
        print("All checks passed. Release remains a draft. Use --publish to publish it.")


if __name__ == "__main__":
    main()
