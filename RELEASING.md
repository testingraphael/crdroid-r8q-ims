# Release workflow

This project publishes through the checked-in CLI workflow in `tools/publish-release.py`. It requires Python 3.11 or newer and an authenticated GitHub CLI with repository and release access. It does not require GitHub Actions permissions.

1. Prepare the release manifest, checksums, installation guide and source on a branch. Run Python compilation, `sh -n` on the module and recovery scripts, and `python3 tools/verify-release.py`.
2. Review the changes in a pull request, resolve findings, and merge it into `main`.
3. Check out the clean merged `main`. Create a lightweight release tag at that exact commit, then create a draft GitHub release and upload the seven files plus `SHA256SUMS` and `release-manifest.json`.
4. Run `python3 tools/publish-release.py --publish` from the repository. The script checks the merged pull request, main branch, tag, asset names, upload state, sizes and GitHub SHA-256 digests. It downloads every file and verifies the bytes against the committed metadata before publishing.

The script refuses an already-published release. Do not replace tested assets in a published release. Use a new version and manifest for changed files. Device tests and independent source review remain separate from release integrity checks.
