#!/usr/bin/env bash
# Removes the files installed by install.sh.
#   tools/uninstall.sh [--purge] [prefix]
# --purge also removes the settings (~/.config/chuds-fg.conf, the
# copies in Flatpak / Snap launchers) and the cache (~/.cache/chuds-fg:
# session, game status, online_tune results); without it they stay, for a
# later install.
set -euo pipefail
purge=0
if [ "${1:-}" = --purge ]; then purge=1; shift; fi
PREFIX="${1:-$HOME/.local}"
rm -fv "$PREFIX/lib/libVkLayer_chuds_fg.so" \
       "$PREFIX/lib32/libVkLayer_chuds_fg.so" \
       "$PREFIX/share/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg_32.json" \
       "$PREFIX/share/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json" \
       "$PREFIX/bin/chuds-fg" "$PREFIX/bin/chuds-fg-gui" "$PREFIX/bin/chuds_fg_demo" \
       "$PREFIX/share/applications/chuds-fg.desktop"
rm -rfv "$PREFIX/share/chuds-fg"
# The copies made for Flatpak launchers (packaging/linux/flatpak.sh).
here="$(cd "$(dirname "$0")" && pwd)"
for f in "$here/flatpak.sh" "$here/../packaging/linux/flatpak.sh"; do
  if [ -f "$f" ]; then bash "$f" --remove; break; fi
done
if [ "$purge" = 1 ]; then
  rm -fv "${XDG_CONFIG_HOME:-$HOME/.config}/chuds-fg.conf"
  rm -rfv "${XDG_CACHE_HOME:-$HOME/.cache}/chuds-fg"
  for d in "$HOME"/.var/app/*/config "$HOME"/snap/*/current/.config; do
    [ -f "$d/chuds-fg.conf" ] && rm -fv "$d/chuds-fg.conf"
  done
  for d in "$HOME"/.var/app/*/.cache/chuds-fg "$HOME"/snap/*/current/.cache/chuds-fg; do
    [ -d "$d" ] && rm -rfv "$d"
  done
fi
true
