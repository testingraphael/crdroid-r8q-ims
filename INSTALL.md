# Installation

These are the steps used for SM-G781B/r8q with firmware `G781BXXSIHYJ1`. Read them before starting. The process erases data. Bootloader unlocking can trip Knox permanently. Keep matching Samsung firmware available before wiping.

## 1. Prepare

Use a reliable USB cable, a charged phone, current [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools), [samloader-rs 2.2.0](https://github.com/topjohnwu/samloader-rs/releases/tag/2.2.0), and the release files in one directory. Command examples use a macOS/Linux shell; samloader also has Windows builds. Use the matching executable for your host.

Confirm the actual model in Samsung Settings. This release targets SM-G781B, not Exynos r8s or a different r8q variant. The tested starting software was Samsung Android 13, XSA, baseband/bootloader `G781BXXSIHYJ1`.

1. Back up data outside the phone and remove all Google accounts through Settings.
2. Unlock the bootloader using the [SM-G781B device guide](https://lineageos.github.io/lineage_wiki/devices/r8q/install/variant2/). Complete Samsung setup afterward, connect to the internet, and confirm OEM unlocking is greyed out and indicates the already-unlocked bootloader.
3. Enable USB debugging and authorize your computer.
4. Obtain matching stock firmware for your exact model, region and bootloader revision. Keep the full package and verify its archive/component checksums.
5. Clone this repository or download its source ZIP. Open a terminal in its root directory, the one containing `README.md` and `tools/`. Download all seven files listed in `SHA256SUMS`, plus `SHA256SUMS` itself, into that same directory. Keep the terminal there for every command in this guide. Check the hashes:

```sh
# Linux
sha256sum -c SHA256SUMS
# macOS
shasum -a 256 -c SHA256SUMS
```

Do not flash a PIT, use a size-check bypass, change CSC, relock the bootloader or write modem/EFS/NV/identifier partitions during this procedure.

The LineageOS link supplies the device's bootloader and transport steps. Use this release's ROM and recovery files for this installation.

## 2. Install vbmeta

With USB debugging authorized:

```sh
adb reboot download
samloader flash --partition VBMETA vbmeta-r8q.img
```

Samsung may boot to a recovery message saying it cannot load Android or that data is corrupt. Select **Factory data reset** and confirm. Complete Samsung setup again, skip account sign-ins, connect to Wi-Fi and re-enable USB debugging. Verify OEM unlocking still indicates the unlocked bootloader.

## 3. Install recovery

```sh
adb reboot download
samloader flash --partition RECOVERY recovery-r8q-g781b.img --no-reboot
```

After the command succeeds, the phone can still say Downloading. Keep USB connected. Hold Volume Down + Side/Power until the screen turns black, then immediately switch to Volume Up + Side/Power. Hold until the custom recovery menu appears.

Boot directly into recovery. Booting Samsung first can replace it. If USB protocol negotiation fails after an earlier Download Mode operation, restart the phone and enter a fresh Download Mode session. Do not bypass the size checks.

## 4. Check the layout

The expected capacities are:

| Partition | Bytes |
| --- | ---: |
| BOOT | 67,108,864 |
| RECOVERY | 82,694,144 |
| DTBO | 10,485,760 |
| SUPER | 10,292,822,016 |
| VBMETA | 65,536 |

In recovery select Apply update, then Apply from ADB:

```sh
adb sideload r8q-read-super-v2.zip
```

Accept the signature warning for this hash-verified local diagnostic. It checks those capacities and reads the first 1 MiB of super into recovery RAM. It does not flash or format a partition. Wait for **Read-only diagnostic complete**.

Return to Advanced > Enable ADB. Pull the files before rebooting:

```sh
mkdir -p private-evidence
adb pull /tmp/r8q-ims-geometry.txt private-evidence/r8q-live-geometry.txt
adb pull /tmp/r8q-ims-super-prefix.bin private-evidence/r8q-live-super-prefix.bin
```

From the same repository root directory, run:

```sh
python3 tools/inspect-super.py \
  --capture private-evidence/r8q-live-super-prefix.bin \
  --report private-evidence/r8q-live-geometry.txt \
  --rom-layout rom-layout.json
```

Continue only if the checksum, geometry, bounds and aligned feasibility checks pass. Recovery's production ADB cannot run as root; use the diagnostic rather than changing SELinux or guessing the layout.

## 5. Install crDroid

In recovery, select Factory reset > Format data/factory reset and confirm. Then select Apply update > Apply from ADB.

```sh
adb sideload crDroidAndroid-16.0-20260526-r8q-v12.10-g781b-fit.zip
```

This locally repacked ZIP is unsigned. Accept its expected signature warning only after verifying the release hash. Wait for recovery to report a successful install or status 0. ADB stopping around 47 percent is not itself the installation result.

Select Reboot system now. Complete crDroid setup and enable USB debugging. Confirm:

```sh
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.build.version.incremental
adb shell getprop gsm.version.baseband
adb shell getenforce
```

Expected values are `16`, `36`, `1779797346`, `G781BXXSIHYJ1` and `Enforcing`. Check data before adding IMS. The ROM uses a Samsung-style fingerprint and overrides Android-visible boot-state properties; those values do not prove that the physical bootloader is locked.

## 6. Install Magisk

Download the official [Magisk 31.1 APK](https://github.com/topjohnwu/Magisk/releases/tag/v31.1). Install it:

```sh
adb install Magisk-v31.1.apk
adb push boot-r8q-unpatched.img /sdcard/Download/boot-r8q-unpatched.img
```

Open Magisk and confirm **Ramdisk Yes**. In its Magisk card choose Install, scroll to Patch firmware/image, select storage, and pick `boot-r8q-unpatched.img`. Wait for Done. Copy the resulting image to the computer using its exact filename:

```sh
adb shell ls /sdcard/Download/magisk_patched-31100_*.img
adb pull /sdcard/Download/magisk_patched-31100_EXACTNAME.img boot-magisk.img
```

Patch on the phone that will use the image. Do not download another person's Magisk-patched boot. Check its header and size before flashing:

```sh
python3 -c 'from pathlib import Path; p=Path("boot-magisk.img"); assert p.read_bytes()[:8] == b"ANDROID!"; assert 0 < p.stat().st_size <= 67108864; print("Boot header and size OK")'
```

The file must be at most 67,108,864 bytes. The tested output was exactly that size, kept the original kernel, preserved encryption and used normal boot mode.

Flash only BOOT:

```sh
adb reboot download
samloader flash --partition BOOT boot-magisk.img
```

Let crDroid boot, unlock it and open Magisk. Confirm installed version 31.1. If additional setup is requested, complete it. Magisk 31.1 grants root ahead of time in its Superuser tab; it does not use the older request popup. Grant Shell only if you plan to use root ADB commands below.

## 7. Install the IMS module

First copy the module to phone storage:

```sh
adb push phhims-r8q-trial-0.2.3.zip /sdcard/Download/phhims-r8q-trial-0.2.3.zip
```

In Magisk, open Modules > Install from storage and select that file from Downloads, then reboot. With Shell root granted, the equivalent is:

```sh
adb push phhims-r8q-trial-0.2.3.zip /data/local/tmp/phhims-r8q-trial-0.2.3.zip
adb shell "su -c 'magisk --install-module /data/local/tmp/phhims-r8q-trial-0.2.3.zip'"
adb reboot
```

Keep the module's device, build and active-APK checks enabled. The tested configuration uses the ROM's existing APNs; do not copy another carrier's APNs or provisioning overrides.

After boot, confirm the package and overlays:

```sh
adb shell pm path me.phh.ims
adb shell cmd overlay list --user 0
adb shell cmd overlay lookup com.android.phone com.android.phone:string/config_ims_mmtel_package
adb shell getenforce
```

The provider should be `me.phh.ims`, with all three `me.phh.ims.trial.*` overlays enabled and SELinux enforcing. Check fresh registration, ordinary incoming/outgoing calls, two-way audio, SMS, LTE data, reboot and airplane recovery on your SIM. Emergency calling has not been validated; do not dial emergency numbers as a test.

## Disable or remove the IMS module

The default CarrierConfig bundle is cached. Run the retained helper before a disable reboot:

```sh
adb shell "su -c 'sh /data/adb/phhims-r8q-cache-refresh.sh && touch /data/adb/modules/phhims_r8q_trial/disable'"
adb reboot
```

The helper removes only derived default bundles and retains persistent override files. After boot, verify that the app, overlays and mounts are gone and the original availability value returns. This disable path was exercised successfully; cellular data continued to work.

Re-enable:

```sh
adb shell "su -c 'rm -f /data/adb/modules/phhims_r8q_trial/disable'"
adb reboot
```

For removal, use Magisk's module removal action and reboot. Its uninstall script attempts the same cache refresh and records a verification marker. The helper remains outside the module so it can be rerun after removal if needed:

```sh
adb shell "su -c 'sh /data/adb/phhims-r8q-cache-refresh.sh'"
adb reboot
```

Check the final configuration after reboot. A helper invocation alone is not proof of restoration. Delete the retained helper and marker only after verifying removal.

If Android fails to boot and recovery can access `/data`, create a module-disable marker:

```sh
touch /data/adb/modules/phhims_r8q_trial/disable
```

The module also stops mounting after two incomplete boots. A completed boot with a calling problem still needs manual rollback.

## Return to Samsung

Keep a verified full stock package for your exact SM-G781B region and bootloader revision. The experiment retained matching XSA `G781BXXSIHYJ1` files from Samsung FUS. A full stock restoration was not performed in this test.

Restore the matching stock system set together, then use stock recovery for the required factory reset. The changed partitions are BOOT, RECOVERY, DTBO, SUPER and VBMETA. Keep the bootloader unlocked until the complete stock installation has booted and the model-specific relocking requirements are established.

Do not blindly flash the full AP or CSC archives with samloader. AP includes PERSIST and other files beyond this procedure, CSC can include a PIT, and CP writes modem firmware. Use the device-specific stock restore procedure for the package and host tools you have verified. Stock restoration cannot recover erased data or reset Knox.
