#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Package a source-built PhhIms APK with the restricted r8q trial module."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--password-file", type=Path, required=True)
    parser.add_argument("--packaging-source", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    apk = args.apk.resolve()
    bt = args.sdk.resolve() / "build-tools/35.0.0"
    android = args.sdk.resolve() / "platforms/android-33/android.jar"
    receipt = json.loads(args.build_receipt.read_text())
    apk_hash = hashlib.sha256(apk.read_bytes()).hexdigest()
    if receipt["apk_sha256"] != apk_hash:
        raise RuntimeError("APK differs from the recorded source build")
    signer = subprocess.run([str(bt / "apksigner"), "verify", "--print-certs", str(apk)],
                            check=True, capture_output=True, text=True).stdout
    if receipt["apk_signer_sha256"] not in signer:
        raise RuntimeError("APK signer differs from the source-build receipt")
    badging = subprocess.run([str(bt / "aapt2"), "dump", "badging", str(apk)],
                             check=True, capture_output=True, text=True).stdout
    manifest_tree = subprocess.run([str(bt / "aapt2"), "dump", "xmltree", str(apk),
                                    "--file", "AndroidManifest.xml"], check=True,
                                   capture_output=True, text=True).stdout
    if not badging.startswith("package: name='me.phh.ims' ") or "sharedUserId" in manifest_tree:
        raise RuntimeError("Unexpected APK identity or shared UID")
    if "application-debuggable" in badging:
        raise RuntimeError("Use a signed release APK without the debuggable flag")
    if "E: protected-broadcast" in manifest_tree:
        raise RuntimeError("Protected registration broadcast remains in APK")
    if "android.permission.BIND_IMS_SERVICE" not in manifest_tree:
        raise RuntimeError("IMS service binding permission is missing")
    permissions = set(re.findall(r"^uses-permission: name='([^']+)'", badging, re.M))
    with zipfile.ZipFile(apk) as package:
        for name in package.namelist():
            if name.endswith(".dex"):
                dex = package.read(name)
                if b"ensureVolteCarrierConfig" in dex or b"overrideConfig" in dex:
                    raise RuntimeError("Carrier configuration writer remains in the APK")
        if "lib/arm64-v8a/libwebrtc_aec_jni.so" not in package.namelist():
            raise RuntimeError("Expected ARM64 native library is missing")
    with tempfile.TemporaryDirectory(prefix="phhims-trial-") as temp:
        work = Path(temp)
        module = work / "module"
        shutil.copytree(ROOT / "module", module)
        source = args.packaging_source.resolve()
        lock = json.loads((ROOT / "source-lock.json").read_text())
        if receipt["source_lock_sha256"] != hashlib.sha256((ROOT / "source-lock.json").read_bytes()).hexdigest():
            raise RuntimeError("Source lock differs from the build receipt")
        for relative, digest in lock["packaging_files"].items():
            original = source / relative
            if hashlib.sha256(original.read_bytes()).hexdigest() != digest:
                raise RuntimeError("Pinned packaging input changed: " + relative)
            if relative.startswith("module/"):
                target_relative = relative.removeprefix("module/")
                if target_relative.startswith("ovl/system/etc/default-permissions/"):
                    target_relative = target_relative.replace("ovl/system/", "ovl/product/", 1)
                destination = module / target_relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, destination)
        grant_file = module / "ovl/system/etc/permissions/privapp-permissions-phhims.xml"
        grants = ET.parse(grant_file).getroot().find("privapp-permissions")
        if grants.get("package") != "me.phh.ims" or any(node.get("name") not in permissions for node in grants):
            raise RuntimeError("Privilege allowlist differs from APK permissions")
        shutil.copy2(source / "LICENSE", module / "LICENSE")
        target = module / "ovl/system/priv-app/PhhIms/PhhIms.apk"
        target.parent.mkdir(parents=True)
        shutil.copy2(apk, target)
        overlay_dir = module / "ovl/product/overlay"
        overlay_dir.mkdir(parents=True)
        carrier_xml = ET.parse(ROOT / "overlays/carrierconfig/res/xml/vendor.xml").getroot()
        fragments = list(carrier_xml)
        if carrier_xml.tag != "carrier_config_list" or len(fragments) != 1:
            raise RuntimeError("Unexpected carrier availability overlay structure")
        fragment = fragments[0]
        values = list(fragment)
        if fragment.tag != "carrier_config" or fragment.attrib != {"mcc": "505", "mnc": "02", "device": "r8q"}:
            raise RuntimeError("Carrier overlay must remain scoped to the tested Optus PLMN and device")
        if len(values) != 1 or values[0].tag != "boolean" or values[0].attrib != {"name": "carrier_volte_available_bool", "value": "true"}:
            raise RuntimeError("Carrier overlay may change only ordinary VoLTE availability")
        for name in ("android", "phone", "carrierconfig"):
            overlay = ROOT / "overlays" / name
            resources = work / (name + "-resources.zip")
            unsigned = work / (name + "-unsigned.apk")
            aligned = work / (name + "-aligned.apk")
            subprocess.run([str(bt / "aapt2"), "compile", "--dir", str(overlay / "res"),
                            "-o", str(resources)], check=True)
            subprocess.run([str(bt / "aapt2"), "link", "--min-sdk-version", "36",
                            "--target-sdk-version", "36", "--keep-raw-values", "-I", str(android),
                            "--manifest", str(overlay / "AndroidManifest.xml"), "-o", str(unsigned),
                            str(resources)], check=True)
            subprocess.run([str(bt / "zipalign"), "-p", "-f", "4", str(unsigned), str(aligned)], check=True)
            destination = overlay_dir / ("PhhImsTrial" + name.title() + "Overlay.apk")
            subprocess.run([str(bt / "apksigner"), "sign", "--ks", str(args.keystore.resolve()),
                            "--ks-pass", "file:" + str(args.password_file.resolve()),
                            "--v4-signing-enabled", "false", "--out", str(destination), str(aligned)], check=True)
            subprocess.run([str(bt / "apksigner"), "verify", str(destination)], check=True)
        lock["build_receipt"] = receipt
        lock["overlay_signing_certificate"] = subprocess.run(
            ["keytool", "-list", "-v", "-keystore", str(args.keystore.resolve()),
             "-storepass:file", str(args.password_file.resolve())], check=True,
            capture_output=True, text=True).stdout
        (module / "build-record.json").write_text(json.dumps(lock, indent=2) + "\n")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(module.rglob("*")):
                if path.is_file():
                    entry = zipfile.ZipInfo(str(path.relative_to(module)), (1980, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    entry.external_attr = (0o100755 if path.suffix == ".sh" else 0o100644) << 16
                    archive.writestr(entry, path.read_bytes())
    print("Module:", args.output)
    print("SHA-256:", hashlib.sha256(args.output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
