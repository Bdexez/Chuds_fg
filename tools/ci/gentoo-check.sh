#!/usr/bin/env bash
# Builds the Gentoo ebuild (packaging/gentoo, a local overlay) from this
# checkout in a stage3 container, both ABIs (abi_x86_32: the 32-bit layer),
# through the ebuild's phases up to the image, and checks it: both layers in
# lib64 / lib, manifests naming them. (Its run-time dependency,
# vulkan-loader[abi_x86_32], is not merged: a 32-bit X/Wayland stack to
# compile.)
#   tools/ci/gentoo-check.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
V="$(sed -n 's/^project(chuds_fg VERSION \([0-9.]*\).*/\1/p' "$ROOT/CMakeLists.txt")"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
tar -C "$ROOT/.." --transform "s#^$(basename "$ROOT")#Chuds_fg-$V#" \
  --exclude-vcs --exclude='build*' --exclude=dist --exclude=__pycache__ \
  -czf "$WORK/chuds-fg-$V.tar.gz" "$(basename "$ROOT")"
docker run --rm -v "$WORK":/w:ro -v "$ROOT/packaging/gentoo":/overlay-src:ro -e V="$V" gentoo/stage3 bash -euo pipefail -c '
  emerge-webrsync -q >/dev/null 2>&1
  # Binary packages for the build tools (compiling cmake / shaderc takes long).
  emerge -q --getbinpkg --oneshot dev-build/cmake dev-util/vulkan-headers dev-util/glslang >/tmp/deps.log 2>&1 ||
    { tail -30 /tmp/deps.log; exit 1; }
  cp -r /overlay-src /var/db/repos/chuds-fg
  mkdir -p /etc/portage/repos.conf
  printf "[chuds-fg]\nlocation = /var/db/repos/chuds-fg\n" > /etc/portage/repos.conf/chuds-fg.conf
  cd /var/db/repos/chuds-fg/games-util/chuds-fg
  cp chuds-fg-9999.ebuild chuds-fg-$V.ebuild
  mkdir -p /var/cache/distfiles && cp /w/chuds-fg-$V.tar.gz /var/cache/distfiles/
  ebuild chuds-fg-$V.ebuild manifest >/dev/null
  export ABI_X86="64 32" USE="-gui"
  ebuild chuds-fg-$V.ebuild clean install > /tmp/ebuild.log 2>&1 || { tail -50 /tmp/ebuild.log; exit 1; }
  img=/var/tmp/portage/games-util/chuds-fg-$V/image
  (cd $img && find . -type f | sort)
  file -L $img/usr/lib64/libVkLayer_chuds_fg.so | grep -q "ELF 64-bit"
  file -L $img/usr/lib/libVkLayer_chuds_fg.so | grep -q "ELF 32-bit"
  grep -h library_path $img/usr/share/vulkan/implicit_layer.d/*.json
  grep -q "\"/usr/lib/libVkLayer_chuds_fg.so\"" $img/usr/share/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg_32.json
  [ ! -e $img/usr/bin/chuds-fg-gui ] && [ -e $img/usr/bin/chuds-fg ]
  echo "gentoo ebuild OK"
'
