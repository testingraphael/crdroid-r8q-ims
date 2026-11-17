#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only

MODDIR=${0%/*}
. "$MODDIR/common.sh"
trial_compatible || exit 0
trial_disabled && exit 0
[ -f /dev/phhims_r8q_trial/ready ] || exit 0

while [ "$(getprop sys.boot_completed)" != 1 ]; do sleep 5; done
sleep 60
trial_disabled && exit 0
trial_compatible || exit 0
echo 0 > /data/adb/phhims-r8q-trial.bootcount
echo "$(date '+%F %T') Boot completed; trial boot counter reset." >> /data/adb/phhims-r8q-trial.log
