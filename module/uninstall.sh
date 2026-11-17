#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only

MODDIR=${0%/*}
umask 077
MARKER=/data/adb/phhims-r8q-cache-refresh.pending
LOG=/data/adb/phhims-r8q-trial.log
if sh "$MODDIR/cache-refresh.sh" >> "$LOG" 2>&1; then
  echo "Cache refresh ran during removal. Verify effective carrier config after reboot." > "$MARKER"
else
  echo "Cache refresh failed during removal. Run the retained helper and reboot, then verify config." > "$MARKER"
  echo "Default carrier cache refresh failed; post-removal verification is required." >> "$LOG"
fi
rm -f /data/adb/phhims-r8q-trial.bootcount
# Keep the diagnostic log and manual-disable marker for deliberate review.
# This module never writes persistent carrier configuration or radio properties.
