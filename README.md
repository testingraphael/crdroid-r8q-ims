> **Warning: this was slop coded. Back up your data before flashing and use it at your own risk.**

# crDroid Android 16 + IMS for Galaxy S20 FE 5G

Unofficial crDroid 12.10 for **Samsung SM-G781B / r8q**, with a companion PhhIms module. This publishes the ROM and module used in the local Aussie Broadband / Optus test.

The ROM is based on Joaquim Miguel's 26 May 2026 build. Its boot, DTBO and super layout were adapted to the tested SM-G781B partition sizes. IMS is installed through Magisk, not baked into the ROM.

**Emergency calling has not been validated. Do not call 000 or another emergency number as a test.**

## Downloads

Get the files from [Releases](https://github.com/testingraphael/crdroid-r8q-ims/releases/latest). Check them against `SHA256SUMS` before flashing.

| File | Use |
| --- | --- |
| `crDroidAndroid-16.0-20260526-r8q-v12.10-g781b-fit.zip` | Adapted Android 16 ROM |
| `phhims-r8q-trial-0.2.3.zip` | Magisk IMS module |
| `recovery-r8q-g781b.img` | Matching recovery fitted to this partition layout |
| `vbmeta-r8q.img` | Verification metadata used for installation |
| `boot-r8q-unpatched.img` | ROM boot image to patch on your own phone with Magisk |
| `r8q-read-super-v2.zip` | Read-only recovery partition diagnostic |
| `phhims-r8q-source-0.2.3.tar.gz` | Patched app/native source and adaptation source |
| `SHA256SUMS` | Checksums for the seven release files above |

## Tested setup

- SM-G781B, r8q, Samsung Android 13 firmware `G781BXXSIHYJ1`.
- crDroid 12.10, Android 16, SDK 36, build `1779797346`.
- Magisk 31.1 and this module 0.2.3, with SELinux enforcing.
- Aussie Broadband Mobile on Optus, PLMN 50502.
- SMS and incoming/outgoing calls with two-way audio reported by the tester. Android marks a short outgoing call as VoLTE and HD.
- Cellular HTTPS, IMS recovery after airplane mode and reboot, and module disable/re-enable checked.

## Install

Follow [INSTALL.md](INSTALL.md) in order. The installation wipes data. The module checks the exact ROM, firmware and CarrierConfig APK, so keep those checks enabled.

1. Start from the matching Samsung Android 13 firmware with an unlocked bootloader. Remove Google accounts and back up data.
2. Flash `vbmeta-r8q.img`, finish the required Samsung reset/setup, then flash `recovery-r8q-g781b.img`.
3. Verify the partition layout, format data in recovery and sideload the adapted ROM ZIP.
4. Boot crDroid. Install official Magisk 31.1 and patch `boot-r8q-unpatched.img` on that same phone.
5. Verify and flash the resulting patched BOOT image. Boot Android, then install `phhims-r8q-trial-0.2.3.zip` in Magisk and reboot.
6. Check ordinary calls, SMS and data on your SIM.

## Source

- [BUILD.md](BUILD.md) explains how to build the app/module and reproduce the ROM geometry patch.
- `module/` contains the Magisk scripts, `overlays/` the Android resources, and `patches/` the PhhIms changes.
- [source-lock.json](source-lock.json) pins the app, native sources and upstream packaging inputs.
- [apk-build-receipt.json](apk-build-receipt.json) records the tested APK build.
- [SOURCES.md](SOURCES.md) contains attribution and upstream source links.

The module enables the IMS provider and an Optus-scoped ordinary VoLTE availability setting. It leaves provisioning and emergency settings unchanged. It refreshes only derived default CarrierConfig cache files and preserves persistent override files.

## Remove or restore

See [INSTALL.md#disable-or-remove-the-ims-module](INSTALL.md#disable-or-remove-the-ims-module) for the tested module rollback and the stock restore preparation. The retained cache helper is part of that procedure.

## Credits

[crDroid](https://github.com/crdroidandroid), [Joaquim Miguel](https://github.com/joaquimiguel), [phhusson](https://github.com/phhusson/ims), [krazey](https://github.com/krazey/ims), [buddi0812](https://github.com/buddi0812/r8q-volte-phhims), [Silvertax](https://github.com/Silvertax/phhims-volte-o2) and the LineageOS r8q maintainers.
