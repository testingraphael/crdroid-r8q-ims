#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only

refresh_default_cache_dir() {
  local directory=$1 file count=0
  [ -d "$directory" ] && [ ! -L "$directory" ] &&
  [ -r "$directory" ] && [ -x "$directory" ] &&
  ls -A "$directory" >/dev/null 2>&1 || return 1
  for file in "$directory"/carrierconfig-com.android.carrierconfig-*.xml; do
    case "${file##*/}" in
      carrierconfig-com.android.carrierconfig-override-*) continue ;;
    esac
    [ -f "$file" ] && [ ! -L "$file" ] || continue
    rm -f "$file" 2>/dev/null || return 1
    count=$((count + 1))
  done
  printf '%s\n' "$count"
}

refresh_default_cache_main() {
  [ "$(id -u)" = 0 ] || return 1
  [ "$(getprop ro.product.device)" = r8q ] &&
  [ "$(getprop ro.build.version.sdk)" = 36 ] &&
  [ "$(getprop ro.build.version.incremental)" = 1779797346 ] || return 1
  local actual count directory=/data/user_de/0/com.android.phone/files
  actual=$(sha256sum /system_ext/priv-app/CarrierConfig/CarrierConfig.apk) || return 1
  [ "${actual%% *}" = 0a3e1ec08fab543e9c52b0fdb1ad40f9f23ca9a513f4f69b83c9002b3d8818dd ] || return 1
  # TeleService on the verified ROM defaults to device-protected storage.
  count=$(refresh_default_cache_dir "$directory") || {
    echo "Cannot inspect the verified device-protected carrier cache directory." >&2
    return 1
  }
  echo "Invalidated $count default CarrierConfig cache files; persistent overrides retained."
}

case "${0##*/}" in
  cache-refresh.sh|phhims-r8q-cache-refresh.sh) refresh_default_cache_main ;;
esac
