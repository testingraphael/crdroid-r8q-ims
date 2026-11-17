# Build and source instructions

Use Python 3.11 or newer, Git, JDK 17 and a local Android SDK. Install SDK platform 33, build tools 34.0.0 and 35.0.0, NDK 25.1.8937393 and CMake 3.22.1. The source includes full platform compatibility jars. Its app target SDK remains 33; the Android 16 overlays target SDK 36. Changing the app target SDK was not part of this adaptation.

Set `JAVA_HOME` and put its `bin` directory on PATH. On the tested host:

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
```

Prepare a new source directory. This downloads the pinned app, rnnoise, AEC3 and nested Abseil sources, then checks and applies all five patches. Existing output directories are rejected.

```sh
python3 tools/prepare-source.py artifacts/source/phhims-clean
```

Obtain the pinned packaging XML and license without executing its scripts:

```sh
git clone https://github.com/Silvertax/phhims-volte-o2.git artifacts/source/phhims-packaging-clean
git -C artifacts/source/phhims-packaging-clean checkout --detach c94355194a1453ba4a69007aac352d1d0656bda3
```

Create a local signing key. Keep its password file and keystore outside version control. Reuse the same key for this experiment. Different keys produce different APK and module hashes.

```sh
umask 077
mkdir -p toolchains/keys
openssl rand -hex 32 > toolchains/keys/trial-password.txt
keytool -genkeypair -keystore toolchains/keys/phhims-trial.jks -alias phhims-trial \
  -keyalg RSA -keysize 3072 -validity 3650 -dname "CN=Local PhhIms trial" \
  -storepass:file toolchains/keys/trial-password.txt \
  -keypass:file toolchains/keys/trial-password.txt
```

The build script runs the release build, aligns and signs the APK, verifies the signature and writes a `.build.json` receipt beside it. Choose a new output file on each run.

```sh
python3 tools/build-apk.py \
  --source artifacts/source/phhims-clean \
  --sdk toolchains/android-sdk \
  --keystore toolchains/keys/phhims-trial.jks \
  --password-file toolchains/keys/trial-password.txt \
  --output artifacts/PhhIms-local.apk
```

Build the module using that receipt. The packaging script validates the APK identity, signer and manifest, checks the packaging XML against the lock, rejects excluded carrier-write method names in DEX, signs the three overlays and normalizes module ZIP metadata.

```sh
python3 tools/build-module.py \
  --apk artifacts/PhhIms-local.apk \
  --sdk toolchains/android-sdk \
  --keystore toolchains/keys/phhims-trial.jks \
  --password-file toolchains/keys/trial-password.txt \
  --packaging-source artifacts/source/phhims-packaging-clean \
  --build-receipt artifacts/PhhIms-local.build.json \
  --output artifacts/phhims-local.zip
```

The tested toolchain is Gradle 8.5, AGP 8.2.0, Kotlin 1.8.10, OpenJDK 17.0.21, SDK platform 33, build tools 35.0.0, NDK 25.1.8937393 and CMake 3.22.1. Debug and release compilation passed. A second incremental local run produced the same signed APK hash. A fresh source preparation and clean build also passed, with all 47 tasks executed. Its source-tree hash matches, but native library and signing entries differ. Bit-for-bit reproducibility is not established. The receipt records local observations, not an independent source attestation.

## ROM image adaptation

The original OTA has oversized boot and DTBO padding and super geometry. Preserve it. `tools/fit-image-padding.py` checks the original image hash, uses AOSP avbtool to resize a separate copy, compares payload and embedded vbmeta bytes, and runs AVB verification.

`tools/adapt-rom.py` verifies the original OTA and official r8q empty-super hashes, checks the saved phone PIT capacities, adjusts boot and DTBO padding, and replaces the dynamic-group limit and empty-super image. It checks CRCs and verifies all unrelated entry contents remain unchanged. Its allocation calculation is not a liblp execution test. The expected sizes are in [INSTALL.md](INSTALL.md), with hashes in the release SHA256SUMS.

Fetch the original ROM from the maintainer link in [SOURCES.md](SOURCES.md). Install samloader-rs 2.2.0. Obtain the pinned AOSP tool and official geometry image:

```sh
mkdir -p toolchains artifacts/crdroid-g781b private-evidence
python3 - <<'PY_DOWNLOAD'
from pathlib import Path
import urllib.request, base64, hashlib
url = "https://android.googlesource.com/platform/external/avb/+/refs/tags/android-16.0.0_r1/avbtool.py?format=TEXT"
data = base64.b64decode(urllib.request.urlopen(url).read())
assert hashlib.sha256(data).hexdigest() == "e5a664a38db623da00f080219bc0ee60a640a9dc4a872803616fae4938ac749b"
Path("toolchains/avbtool-android16.py").write_bytes(data)
url = "https://mirrorbits.lineageos.org/full/r8q/20261115/super_empty.img"
data = urllib.request.urlopen(url).read()
assert hashlib.sha256(data).hexdigest() == "1ba50b964ac6d8eefa5009456f358d530805658142cc921eec8bcf24c79792e3"
Path("artifacts/crdroid-g781b/super_empty.img").write_bytes(data)
PY_DOWNLOAD
```

The adapter also requires the phone's read-only PIT capture. In a fresh Download Mode session use `samloader dump-pit --output private-evidence/r8q-original.pit --no-reboot`, then restart the phone before the next Download Mode operation. Keep the PIT private and do not flash it. The example below assumes the verified samloader executable was placed at `toolchains/samloader-2.2.0/samloader`.

```sh
python3 tools/adapt-rom.py \
  --input artifacts/crDroidAndroid-16.0-20260526-r8q-v12.10.zip \
  --output artifacts/crDroidAndroid-16.0-20260526-r8q-v12.10-g781b-fit.zip \
  --pit private-evidence/r8q-original.pit \
  --samloader toolchains/samloader-2.2.0/samloader \
  --avbtool toolchains/avbtool-android16.py \
  --super-empty artifacts/crdroid-g781b/super_empty.img
```

The local OTA loses its whole-file signature after repacking. Existing device metadata takes precedence over its fallback empty image. Inspect the actual super layout in custom recovery before applying it. The relevant two-argument updater source is in [LineageOS deprecated-ota](https://github.com/LineageOS/android_bootable_deprecated-ota/blob/lineage-23.2/updater/updater_runtime_dynamic_partitions.cpp). Unique strings in the bundled binary support this correspondence, but no exact build manifest establishes a bit-identical source mapping.
