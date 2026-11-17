#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Recovery update-binary interface. Write diagnostic output only to /tmp.

OUTFD=$2
case "$OUTFD" in ''|*[!0-9]*) exit 1 ;; esac
ui_print() { printf 'ui_print %s\nui_print\n' "$*" > "/proc/self/fd/$OUTFD"; }
fail() { ui_print "$*"; exit 1; }

[ "$(id -u)" = 0 ] || fail "The diagnostic requires recovery's root installer."
[ "$(getprop ro.product.device)" = r8q ] || fail "Unexpected device. Nothing read."
[ "$(getprop ro.build.version.sdk)" = 36 ] || fail "Unexpected recovery SDK. Nothing read."
[ "$(getprop ro.bootloader)" = G781BXXSIHYJ1 ] || fail "Unexpected bootloader. Nothing read."

REPORT=/tmp/r8q-ims-geometry.txt
PREFIX=/tmp/r8q-ims-super-prefix.bin
umask 022
: > "$REPORT" || fail "Cannot create RAM diagnostic report."
for item in boot:67108864 recovery:82694144 dtbo:10485760 super:10292822016 vbmeta:65536; do
  name=${item%%:*}
  expected=${item#*:}
  size=$(blockdev --getsize64 "/dev/block/by-name/$name") || fail "Cannot read $name size."
  [ "$size" = "$expected" ] || fail "Unexpected $name capacity. No metadata read."
  printf '%s %s\n' "$name" "$size" >> "$REPORT" || fail "Cannot record partition size."
done

ui_print "Reading super metadata into recovery RAM. No partition writes."
dd if=/dev/block/by-name/super of="$PREFIX" bs=4096 count=256 2>> "$REPORT" || fail "Metadata read failed."
[ "$(wc -c < "$PREFIX")" -eq 1048576 ] || fail "Metadata read was incomplete."
sha256sum "$PREFIX" >> "$REPORT" || fail "Cannot hash metadata capture."
chmod 0644 "$REPORT" "$PREFIX" || fail "Cannot expose RAM capture to the ADB shell."
chcon u:object_r:shell_data_file:s0 "$REPORT" "$PREFIX" || fail "Cannot label RAM capture for ADB access."
ui_print "Read-only diagnostic complete. Return to recovery, then enable ADB."
