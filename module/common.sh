#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only

carrier_config_compatible() {
  local apk=/system_ext/priv-app/CarrierConfig/CarrierConfig.apk
  local expected=0a3e1ec08fab543e9c52b0fdb1ad40f9f23ca9a513f4f69b83c9002b3d8818dd
  local actual record active work=/dev/phhims_r8q_identity xml
  actual=$(sha256sum "$apk" 2>/dev/null) || return 1
  [ "${actual%% *}" = "$expected" ] || return 1
  # Package settings are ABX. Convert a copy into private RAM without changing them.
  [ ! -L "$work" ] && mkdir -p "$work" && chmod 0700 "$work" || return 1
  xml="$work/packages.$$.xml"
  if ! (umask 077; timeout 8 /system/bin/abx2xml /data/system/packages.xml "$xml" 2>/dev/null); then
    rm -f "$xml"
    return 1
  fi
  if [ "$(grep -c '^[[:space:]]*<package name="com.android.carrierconfig" ' "$xml")" != 1 ]; then
    rm -f "$xml"
    return 1
  fi
  record=$(grep '^[[:space:]]*<package name="com.android.carrierconfig" ' "$xml") || {
    rm -f "$xml"
    return 1
  }
  rm -f "$xml"
  case "$record" in
    *'codePath="/system_ext/priv-app/CarrierConfig"'*) ;;
    *) return 1 ;;
  esac
  if [ "$(getprop sys.boot_completed)" = 1 ]; then
    active=$(pm path com.android.carrierconfig 2>/dev/null) || return 1
    [ "$active" = package:/system_ext/priv-app/CarrierConfig/CarrierConfig.apk ] || return 1
  fi
}

trial_compatible() {
  [ "$(getprop ro.product.device)" = r8q ] &&
  [ "$(getprop ro.build.version.sdk)" = 36 ] &&
  [ "$(getprop ro.build.version.incremental)" = 1779797346 ] &&
  [ "$(getprop ro.build.fingerprint)" = samsung/r8qxx/r8q:11/RP1A.200720.012/G780GXXSHEYJ1:user/release-keys ] &&
  [ "$(getprop ro.bootloader)" = G781BXXSIHYJ1 ] &&
  carrier_config_compatible
}

trial_disabled() {
  [ -f "$MODDIR/disable" ] || [ -f /data/adb/phhims-r8q-trial.disable ]
}
