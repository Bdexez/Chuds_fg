#!/usr/bin/env bash
# The Linux install scripts, in a scratch home (no GPU, no display):
# - packaging/linux/flatpak.sh copies the layer into Flatpak / Snap launchers,
#   reports the copies an update left behind (--check), re-copies them, and
#   removes them;
# - every copy over an installed library goes through a new inode (a running
#   game keeps the library it mapped: an in-place copy truncates it, SIGBUS),
#   in flatpak.sh and in the archive's install.sh.
#   tests/linux_scripts.sh <source dir>
set -euo pipefail
SRC="$(cd "${1:?usage: linux_scripts.sh <source dir>}" && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }

# Every per-user location in the scratch home: the scripts follow the XDG
# variables (uninstall.sh --purge deletes their chuds-fg files).
export HOME="$T/home" XDG_CONFIG_HOME="$T/home/.config" XDG_CACHE_HOME="$T/home/.cache" \
  XDG_DATA_HOME="$T/home/.local/share" XDG_STATE_HOME="$T/home/.local/state"
unset XDG_RUNTIME_DIR CHUDS_FG_CONFIG CHUDS_FG_STATUS_DIR CHUDS_FG_CACHE_DIR
mkdir -p "$HOME/.var/app/com.valvesoftware.Steam" "$HOME/.var/app/net.lutris.Lutris" "$HOME/snap/steam/current"
pre="$T/prefix"
mkdir -p "$pre/lib" "$pre/lib32" "$pre/share/vulkan/implicit_layer.d" "$pre/share/chuds-fg"
echo v1 > "$pre/lib/libVkLayer_chuds_fg.so"
echo v1-32 > "$pre/lib32/libVkLayer_chuds_fg.so"
echo "[*]" > "$pre/share/chuds-fg/profiles.conf"
for s in "" _32; do
  lib=lib; [ -n "$s" ] && lib=lib32
  printf '{"file_format_version": "1.1.2", "layer": {"library_path": "%s"}}\n' \
    "$pre/$lib/libVkLayer_chuds_fg.so" > "$pre/share/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg$s.json"
done
mkdir -p "$XDG_CONFIG_HOME"; echo "enabled = 1" > "$XDG_CONFIG_HOME/chuds-fg.conf"

FP="$SRC/packaging/linux/flatpak.sh"
bash "$FP" "$pre" > /dev/null
steam="$HOME/.var/app/com.valvesoftware.Steam"
copy="$steam/data/chuds-fg/lib/libVkLayer_chuds_fg.so"
snapcopy="$HOME/snap/steam/common/chuds-fg/lib32/libVkLayer_chuds_fg.so"
[ "$(cat "$copy")" = v1 ] || fail "Flatpak copy"
[ "$(cat "$snapcopy")" = v1-32 ] || fail "Snap 32-bit copy"
grep -q "\"library_path\": \"$copy\"" "$steam/data/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json" ||
  fail "Flatpak manifest does not name the copy"
[ -f "$steam/config/chuds-fg.conf" ] || fail "settings not copied"
out="$(bash "$FP" --check "$pre")" || fail "fresh copies reported stale: $out"
[ -z "$out" ] || fail "fresh copies listed: $out"

# An update of the layer: --check lists every copy left behind, exit 1.
echo v2 > "$pre/lib/libVkLayer_chuds_fg.so"
rc=0; out="$(bash "$FP" --check "$pre")" || rc=$?
[ "$rc" = 1 ] || fail "--check exit $rc after an update"
grep -q "^com.valvesoftware.Steam $copy\$" <<<"$out" || fail "Steam copy not listed: $out"
grep -q "^net.lutris.Lutris " <<<"$out" || fail "Lutris copy not listed: $out"
grep -q "^snap:steam .*/lib/libVkLayer" <<<"$out" || fail "Snap copy not listed: $out"
if grep -q "lib32" <<<"$out"; then fail "unchanged 32-bit copy listed: $out"; fi

# Re-copy while a "game" holds the old library open: it keeps its inode.
exec 9< "$copy"
ino="$(stat -c %i "$copy")"
bash "$FP" "$pre" > /dev/null
[ "$(stat -c %i "$copy")" != "$ino" ] || fail "flatpak.sh copied over the installed library in place"
[ "$(cat <&9)" = v1 ] || fail "the open library changed under the game"
exec 9<&-
[ "$(cat "$copy")" = v2 ] || fail "copy not refreshed"
bash "$FP" --check "$pre" > /dev/null || fail "still stale after the re-copy"
ls "$steam/data/chuds-fg/lib/" | grep -q tmp && fail "temporary file left behind"

bash "$FP" --remove > /dev/null
[ ! -e "$copy" ] && [ ! -e "$steam/data/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json" ] ||
  fail "--remove left the Flatpak copy"
[ ! -e "$snapcopy" ] || fail "--remove left the Snap copy"

# The Flatpak extension installed for Steam's runtime branch: no copy there
# (old ones removed), the settings and a mark for the panel; Lutris, on a
# branch the extension is not installed for, keeps its copy.
fl="$HOME/.local/share/flatpak"
mkdir -p "$fl/app/com.valvesoftware.Steam/current/active" "$fl/app/net.lutris.Lutris/current/active" \
  "$fl/runtime/org.freedesktop.Platform.VulkanLayer.ChudsFg/$(uname -m)/25.08"
printf '[Application]\nname=com.valvesoftware.Steam\nruntime=org.freedesktop.Platform/x86_64/25.08\n' \
  > "$fl/app/com.valvesoftware.Steam/current/active/metadata"
printf '[Application]\nruntime=org.freedesktop.Platform/x86_64/24.08\n' > "$fl/app/net.lutris.Lutris/current/active/metadata"
bash "$FP" "$pre" > /dev/null
bash "$FP" "$pre" > "$T/out"   # twice: the second run finds the first one's state
grep -q "com.valvesoftware.Steam (Flatpak): layer provided by the .* extension (25.08)" "$T/out" || fail "extension not seen: $(cat "$T/out")"
[ ! -e "$copy" ] && [ ! -e "$steam/data/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json" ] ||
  fail "a copy left beside the extension"
[ "$(cat "$steam/data/chuds-fg/extension")" = 25.08 ] || fail "no extension mark"
[ -f "$steam/config/chuds-fg.conf" ] || fail "settings not copied for the extension"
[ -f "$HOME/.var/app/net.lutris.Lutris/data/chuds-fg/lib/libVkLayer_chuds_fg.so" ] ||
  fail "Lutris (other branch) lost its copy"
bash "$FP" --check "$pre" > /dev/null || fail "--check on the extension's app"
rm -rf "$fl"
bash "$FP" "$pre" > /dev/null
[ -f "$copy" ] && [ ! -e "$steam/data/chuds-fg/extension" ] || fail "copy not back once the extension is gone"

# The archive's install.sh: new inodes for the libraries it replaces.
arc="$T/archive"
mkdir -p "$arc/files/lib" "$arc/files/share/chuds-fg" "$arc/files/share/vulkan/implicit_layer.d"
cp "$SRC/packaging/linux/install.sh" "$SRC/packaging/linux/flatpak.sh" "$arc/"
uname -m > "$arc/files/share/chuds-fg/ARCH"
echo new > "$arc/files/lib/libVkLayer_chuds_fg.so"
printf '{"layer": {"library_path": "/x/lib/libVkLayer_chuds_fg.so"}}\n' \
  > "$arc/files/share/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json"
inst="$T/installed"
mkdir -p "$inst/lib"; echo old > "$inst/lib/libVkLayer_chuds_fg.so"
exec 9< "$inst/lib/libVkLayer_chuds_fg.so"
bash "$arc/install.sh" "$inst" > /dev/null
[ "$(cat <&9)" = old ] || fail "install.sh copied over the installed library in place"
exec 9<&-
[ "$(cat "$inst/lib/libVkLayer_chuds_fg.so")" = new ] || fail "install.sh did not install"
grep -q "\"library_path\": \"$inst/lib/libVkLayer_chuds_fg.so\"" \
  "$inst/share/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json" || fail "install.sh manifest path"
# uninstall.sh: the installation; --purge also the settings and caches.
cp "$SRC/tools/uninstall.sh" "$arc/"
mkdir -p "$HOME/.cache/chuds-fg/run" "$steam/.cache/chuds-fg/run"
bash "$arc/uninstall.sh" "$inst" > /dev/null
[ ! -e "$inst/lib/libVkLayer_chuds_fg.so" ] || fail "uninstall.sh left the layer"
[ -f "$XDG_CONFIG_HOME/chuds-fg.conf" ] || fail "uninstall.sh without --purge removed the settings"
bash "$arc/uninstall.sh" --purge "$inst" > /dev/null
[ ! -e "$XDG_CONFIG_HOME/chuds-fg.conf" ] && [ ! -e "$HOME/.cache/chuds-fg" ] &&
  [ ! -e "$steam/config/chuds-fg.conf" ] && [ ! -e "$steam/.cache/chuds-fg" ] ||
  fail "--purge left settings: $(ls -d "$XDG_CONFIG_HOME/chuds-fg.conf" "$HOME/.cache/chuds-fg" "$steam/config/chuds-fg.conf" "$steam/.cache/chuds-fg" 2>/dev/null)"

# chuds-fg --gpu: the GPU the screen is plugged into, by type, by vendor.
CLI="$SRC/tools/chuds-fg"
drm="$T/drm"; mkdir -p "$drm/card0/device" "$drm/card1/device" "$drm/card0-eDP-1" "$drm/card1-HDMI-A-1"
echo 0x8086 > "$drm/card0/device/vendor"; echo 0x46a6 > "$drm/card0/device/device"
echo 0x10de > "$drm/card1/device/vendor"; echo 0x25a2 > "$drm/card1/device/device"
echo connected > "$drm/card0-eDP-1/status"; echo disconnected > "$drm/card1-HDMI-A-1/status"
export CHUDS_FG_DRM_DIR="$drm" CHUDS_FG_GPU_LIST=$'0x8086 0x46a6 INTEGRATED Intel(R) Iris(R) Xe Graphics\n0x10de 0x25a2 DISCRETE NVIDIA GeForce RTX 3050 Laptop GPU'
env_of() { bash "$CLI" --gpu "$1" -- env 2>/dev/null; }
out="$(env_of screen)"
grep -qx "MESA_VK_DEVICE_SELECT=8086:46a6" <<<"$out" && grep -qx "__VK_LAYER_NV_optimus=non_NVIDIA_only" <<<"$out" ||
  fail "--gpu screen: $out"
grep -qx "DXVK_FILTER_DEVICE_NAME=Intel(R) Iris(R) Xe Graphics" <<<"$out" || fail "--gpu screen: no DXVK filter"
out="$(env_of discrete)"
grep -qx "MESA_VK_DEVICE_SELECT=10de:25a2" <<<"$out" && grep -qx "__NV_PRIME_RENDER_OFFLOAD=1" <<<"$out" ||
  fail "--gpu discrete: $out"
[ "$(env_of nvidia | grep MESA_VK_DEVICE_SELECT=)" = "MESA_VK_DEVICE_SELECT=10de:25a2" ] || fail "--gpu nvidia"
grep -q "0x8086:0x46a6  integrated  Intel(R) Iris(R) Xe Graphics  ← screen" <<<"$(bash "$CLI" --gpu list)" || fail "--gpu list"
if bash "$CLI" --gpu amd -- true 2>/dev/null; then fail "--gpu amd without an AMD GPU"; fi
bash "$CLI" --help | tail -1 | grep -q -- "-h, --help" || fail "--help cut short"
# --issue-url: the form's fields from a report, the home's path hidden.
cat > "$T/report.txt" <<REPORT
== chuds-fg diagnostic report, 2026-10-02 12:00 UTC

== lecture rapide (à faire pendant que le jeu tourne, après « Démarrer »)
panneau : ouvert, cible pid 42 — écran 144 Hz

== system
Linux 6.18 x86_64
PRETTY_NAME="Fedora Linux 44 (Workstation Edition)"
session: wayland  desktop: GNOME  WAYLAND_DISPLAY=wayland-0  DISPLAY=:0

== layer
[chuds-fg     0.000 INFO] VK_LAYER_CHUDS_fg v0.6.0 loaded (enabled=1)
	deviceName         = AMD Radeon RX 7800 XT (RADV NAVI32)
	driverInfo         = Mesa 26.0.1

== installed manifests
-rw-r--r-- 1 u u 600 Oct  2 12:00 $HOME/.local/share/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json

== environment
REPORT
url="$(bash "$CLI" --issue-url "$T/report.txt")"
dec="$(python3 -c 'import sys, urllib.parse as u; q = u.parse_qs(u.urlparse(sys.argv[1]).query)
for k in ("version", "distro", "gpu", "session", "install", "quick"): print(k + "=" + q.get(k, [""])[0].replace("\n", " "))' "$url")"
grep -qx "version=0.6.0" <<<"$dec" || fail "issue url version: $dec"
grep -qx "distro=Fedora Linux 44 (Workstation Edition), Linux 6.18 x86_64" <<<"$dec" || fail "issue url distro: $dec"
grep -qx "gpu=AMD Radeon RX 7800 XT (RADV NAVI32), Mesa 26.0.1" <<<"$dec" || fail "issue url gpu: $dec"
grep -qx "install=~/.local/share/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json" <<<"$dec" || fail "issue url install: $dec"
grep -q "^quick=panneau : ouvert, cible pid 42" <<<"$dec" || fail "issue url quick: $dec"
if grep -q "$HOME" <<<"$url$dec"; then fail "the home's path in the issue url"; fi
[[ "$url" == https://github.com/Bdexez/Chuds_fg/issues/new\?template=bug_report.yml\&* ]] || fail "issue url: $url"
echo "linux scripts OK"
