#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Mount staging follows buddi0812 and Silvertax's r8q module.

MODDIR=${0%/*}
. "$MODDIR/common.sh"
trial_compatible || exit 0
trial_disabled && exit 0

LOG=/data/adb/phhims-r8q-trial.log
CNT=/data/adb/phhims-r8q-trial.bootcount
STAGE=/dev/phhims_r8q_trial
log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

if [ -e "$CNT" ]; then
  n=$(cat "$CNT") || exit 1
else
  n=0
fi
case "$n" in ''|*[!0-9]*) log "Invalid boot counter; skipping mounts."; exit 1 ;; esac
n=$((n + 1))
if ! printf '%s\n' "$n" > "$CNT.tmp" || ! mv "$CNT.tmp" "$CNT" ||
   [ "$(cat "$CNT")" != "$n" ]; then
  log "Cannot persist boot counter; skipping mounts."
  exit 1
fi
if [ "$n" -gt 2 ]; then
  log "Skipping mounts after two incomplete boots."
  exit 0
fi

mkdir -p "$STAGE" || exit 1
rm -f "$STAGE/ready"
cp -R "$MODDIR/ovl/." "$STAGE/" || exit 1
chmod -R a+rX "$STAGE"
chcon -R u:object_r:system_file:s0 "$STAGE" || exit 1

rollback_mounts() {
  # Inspect the mount options so interruption immediately after mount is covered.
  for dst in $(awk -v stage="$STAGE/" '$3 == "overlay" && index($4, "lowerdir=" stage) { print $2 }' /proc/mounts); do
    umount "$dst" || log "Failed to unmount $dst"
  done
}
complete=0
trap '[ "$complete" = 1 ] || rollback_mounts' 0
trap 'exit 1' HUP INT TERM

# Permissions must be visible before the privileged APK can be scanned.
for rel in system/etc/permissions system/etc/sysconfig product/etc/default-permissions product/overlay system/priv-app; do
  src="$STAGE/$rel"
  dst="/$rel"
  if [ ! -d "$src" ] || [ ! -d "$dst" ] ||
     ! mount -t overlay overlay -o "ro,lowerdir=$src:$dst" "$dst"; then
    log "Mount failed for $dst. Removing trial mounts."
    exit 1
  fi
done

sh "$MODDIR/cache-refresh.sh" >> "$LOG" 2>&1 || {
  log "Carrier cache refresh failed. Removing trial mounts."
  exit 1
}

# Staged APK timestamps can predate cached manifests during early boot.
for cache in /data/system/package_cache/*/PhhIms-* /data/system/package_cache/*/PhhImsTrial*; do
  [ ! -f "$cache" ] || rm -f "$cache"
done
touch "$STAGE/ready" || exit 1
complete=1
log "Mounted trial app, permissions and three overlays."
