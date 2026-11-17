#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only

. "$MODPATH/common.sh"
trial_compatible || abort "This trial requires SM-G781B firmware G781BXXSIHYJ1 and crDroid 12.10 build 1779797346, SDK 36."
[ "$(getprop sys.boot_completed)" = 1 ] || abort "Install this module from a fully booted Android system."
[ "$(getenforce)" = Enforcing ] || abort "SELinux must be enforcing."
existing=$(pm list packages -u --user 0 me.phh.ims 2>&1) || abort "Package manager query failed."
case "$existing" in
  '') ;;
  package:*)
    for package in $existing; do
      case "$package" in
        package:me.phh.ims|package:me.phh.ims.trial.android|package:me.phh.ims.trial.phone|package:me.phh.ims.trial.carrierconfig) ;;
        *) abort "An unrelated PhhIms package is present." ;;
      esac
    done
    [ -d /data/adb/modules/phhims_r8q_trial ] || abort "Existing PhhIms is not owned by this trial."
    installed=$(pm path me.phh.ims 2>&1) || abort "Cannot identify the existing PhhIms APK."
    [ "$installed" = package:/system/priv-app/PhhIms/PhhIms.apk ] || abort "Unexpected existing PhhIms path."
    actual=$(sha256sum /system/priv-app/PhhIms/PhhIms.apk) || abort "Cannot hash existing PhhIms."
    prior=$(sha256sum /data/adb/modules/phhims_r8q_trial/ovl/system/priv-app/PhhIms/PhhIms.apk) || abort "Cannot verify trial ownership."
    incoming=$(sha256sum "$MODPATH/ovl/system/priv-app/PhhIms/PhhIms.apk") || abort "Cannot hash incoming PhhIms."
    [ "${actual%% *}" = "${prior%% *}" ] && [ "${actual%% *}" = "${incoming%% *}" ] || abort "Existing PhhIms differs from this trial APK."
    ;;
  *) abort "Package manager returned an unexpected response." ;;
esac
[ ! -d /data/adb/modules/phhims_volte ] || abort "Remove the upstream phhims_volte module first."
set_perm_recursive "$MODPATH" 0 0 0755 0644
for script in common.sh customize.sh post-fs-data.sh service.sh uninstall.sh cache-refresh.sh; do
  set_perm "$MODPATH/$script" 0 0 0755
done
cp "$MODPATH/cache-refresh.sh" /data/adb/phhims-r8q-cache-refresh.sh || abort "Cannot retain the cache rollback helper."
set_perm /data/adb/phhims-r8q-cache-refresh.sh 0 0 0700
ui_print "- Device and build checks passed."
ui_print "- Experimental IMS and an Optus availability trial. Provisioning is unchanged. Emergency calling is unverified."
