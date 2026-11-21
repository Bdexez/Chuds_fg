# Copyright 2026 Bdexez
# Proprietary software, all rights reserved (see LICENSE)

EAPI=8

# The layer for each ABI (abi_x86_32: the 32-bit one, for 32-bit games),
# the launcher, panel and profiles once. A local overlay:
#   packaging/gentoo is one (metadata/layout.conf); tools/ci/gentoo-check.sh

inherit cmake-multilib

DESCRIPTION="Frame generation and upscaling Vulkan layer for games"
HOMEPAGE="https://github.com/Bdexez/Chuds_fg"
if [[ ${PV} == 9999 ]]; then
	inherit git-r3
	EGIT_REPO_URI="https://github.com/Bdexez/Chuds_fg.git"
else
	SRC_URI="https://github.com/Bdexez/Chuds_fg/archive/v${PV}.tar.gz -> ${P}.tar.gz"
	S="${WORKDIR}/Chuds_fg-${PV}"
	KEYWORDS="~amd64 ~arm64"
fi

LICENSE="all-rights-reserved"
RESTRICT="bindist mirror"
SLOT="0"
IUSE="gui"

DEPEND="dev-util/vulkan-headers"
RDEPEND="
	media-libs/vulkan-loader[${MULTILIB_USEDEP}]
	gui? (
		dev-lang/python:*
		dev-python/pygobject:3
		gui-libs/gtk:4[introspection]
	)
"
BDEPEND="|| ( media-libs/shaderc dev-util/glslang )"

multilib_src_configure() {
	local mycmakeargs=(
		-DCHUDS_FG_BUILD_DEMO=OFF
		-DCHUDS_FG_BUILD_TESTS=OFF
		-DCHUDS_FG_BUILD_OFFLINE=OFF
		-DCHUDS_FG_INSTALL_LIBDIR=$(get_libdir)
	)
	# The other ABI's layer: its own manifest (VK_LAYER_CHUDS_fg_32,
	# library_arch 32); the eclass already passes -m32.
	multilib_is_native_abi || mycmakeargs+=( -DCHUDS_FG_32BIT=ON )
	cmake_src_configure
}

multilib_src_install_all() {
	einstalldocs
	if ! use gui; then
		rm -f "${ED}"/usr/bin/chuds-fg-gui "${ED}"/usr/share/applications/chuds-fg.desktop || die
	fi
}

pkg_postinst() {
	elog "The layer loads into every Vulkan game and stays inert until turned on:"
	elog "  chuds-fg-gui (USE=gui), or CHUDS_FG=1 %command% in Steam's launch options."
	elog "Steam, Heroic, Lutris or Bottles installed as a Flatpak? Run once, as your user:"
	elog "  chuds-fg --sandboxes"
}
