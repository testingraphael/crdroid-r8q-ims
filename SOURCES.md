# Sources and attribution

## ROM

- Base ROM by [Joaquim Miguel](https://github.com/joaquimiguel): [original release post](https://t.me/quimsbunker/85), [original download](https://pixeldrain.com/u/abTVebCq).
- Original file: `crDroidAndroid-16.0-20260526-r8q-v12.10.zip`, SHA-256 `122f4bd79ea755ba9a72ec3fdd4b59fbd12a878624743b973eae08e8bd646198`.
- [crDroid source](https://github.com/crdroidandroid), [maintainer device tree](https://github.com/joaquimiguel/android_device_samsung_r8q), [maintainer kernel tree](https://github.com/joaquimiguel/larois-r8q).
- The running kernel identifies [commit 60e3e5c099994a51c79cd03e1afddd9a102d7e62](https://github.com/joaquimiguel/larois-r8q/commit/60e3e5c099994a51c79cd03e1afddd9a102d7e62) and a dirty build. The upstream ROM's complete build manifest was not supplied with the archive.

The local ROM repack changes only boot/DTBO padding and footer positions, the dynamic-group limit and the fallback empty-super geometry. It retains kernel and other image payloads. `rom-layout.json` records the adaptation. The ROM's own component licenses remain applicable; this repository's GPL license does not relicense third-party firmware.

## IMS

[source-lock.json](source-lock.json) contains full revisions and patch hashes.

| Component | Source |
| --- | --- |
| PhhIms | [krazey/ims a3fec01](https://github.com/krazey/ims/tree/a3fec01ebc4f51c39026565c4a451fef454637fa), descended from [phhusson/ims](https://github.com/phhusson/ims) |
| r8q work | [buddi0812](https://github.com/buddi0812/r8q-volte-phhims) and [Silvertax c943551](https://github.com/Silvertax/phhims-volte-o2/tree/c94355194a1453ba4a69007aac352d1d0656bda3) |
| RNNoise | [amikhasenko/rnnoise](https://github.com/amikhasenko/rnnoise/tree/f94e734aa504e34100516c7d486cf69fc4174f00) |
| AEC3 | [ewan-xu/AEC3](https://github.com/ewan-xu/AEC3/tree/6b11f0f31cd10f6bf68025ccad771f545d87dbce) |
| Abseil | [abseil-cpp](https://github.com/abseil/abseil-cpp/tree/852fc61f31b3d68df58ba6a167dff73fee04558f) |

Patches 0001 through 0003 preserve the upstream r8q changes. Patch 0004 removes the persistent CarrierConfig writer. Patch 0005 makes the SDK path and ARM64 build portable. Module scripts and overlays provide the exact-build packaging, permission placement, ordinary availability setting and derived-cache handling.

The release includes the patched app and native source archive. It preserves upstream license files. Local scripts and module changes are GPL-2.0-only; upstream components retain their own notices and licenses. Signing keys are not published.

## Installation tools and images

- [Magisk 31.1](https://github.com/topjohnwu/Magisk/releases/tag/v31.1), downloaded from the official project. Patch the boot image on the target phone.
- [samloader-rs 2.2.0](https://github.com/topjohnwu/samloader-rs/releases/tag/2.2.0).
- [LineageOS r8q images](https://download.lineageos.org/devices/r8q), build 15 November 2026. The released vbmeta and the fallback super geometry were hash-verified against the build API.
- [AOSP avbtool, Android 16 tag](https://android.googlesource.com/platform/external/avb/+/refs/tags/android-16.0.0_r1/avbtool.py), SHA-256 `e5a664a38db623da00f080219bc0ee60a640a9dc4a872803616fae4938ac749b`.

No modem image, EFS content, SIM data, stock Samsung package or device-specific Magisk-patched boot image is included in the release.
