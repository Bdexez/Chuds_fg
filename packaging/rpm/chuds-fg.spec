# Source package for COPR (Fedora, Bazzite / Silverblue through rpm-ostree)
# and the openSUSE Build Service: built from the release tarball, so the
# distribution's own rebuilds keep it current (the prebuilt .rpm of the
# releases is tools/package-native.sh). On x86_64 it also builds the 32-bit
# layer (32-bit games), which needs the i686 / -32bit development packages
# in the build root (COPR: enable "multilib" for the project).
#   rpmbuild -ba packaging/rpm/chuds-fg.spec   (tarball in SOURCES)
#   tools/ci/srpm-check.sh                          (Fedora + openSUSE containers)
%bcond_without lib32

Name:           chuds-fg
Version:        0.5.6
Release:        1%{?dist}
Summary:        Frame generation and upscaling Vulkan layer for games
License:        LicenseRef-proprietary
URL:            https://github.com/Bdexez/Chuds_fg
Source0:        %{url}/archive/v%{version}/Chuds_fg-%{version}.tar.gz

BuildRequires:  cmake >= 3.20
BuildRequires:  gcc-c++
BuildRequires:  vulkan-headers
%if 0%{?suse_version}
BuildRequires:  shaderc
%else
BuildRequires:  glslc
# The C++ runtime linked in (CHUDS_FG_STATIC_RUNTIME, like the release archives):
# games and the Steam runtime may bring an older libstdc++.
BuildRequires:  libstdc++-static%{?_isa}
%endif
%ifarch x86_64
%if %{with lib32}
%if 0%{?suse_version}
BuildRequires:  gcc-c++-32bit
BuildRequires:  glibc-devel-32bit
%else
BuildRequires:  glibc-devel(x86-32)
BuildRequires:  libstdc++-devel(x86-32)
BuildRequires:  libstdc++-static(x86-32)
BuildRequires:  libatomic(x86-32)
# The 64-bit ones too, named: dnf would otherwise satisfy gcc-c++'s
# libstdc++-devel with the i686 package alone (no 64-bit c++config.h), and
# the linker wants both libatomic.
BuildRequires:  libstdc++-devel%{?_isa}
BuildRequires:  libatomic%{?_isa}
%endif
%endif
%endif
Requires:       (vulkan-loader or libvulkan1)
Recommends:     python3-gobject
Recommends:     (gtk4 or typelib-1_0-Gtk-4_0)
Suggests:       vulkan-tools
# The 32-bit layer loads into 32-bit games, which bring their own 32-bit
# glibc: no dependency on it (nor on a 32-bit libstdc++: linked in).
%global __requires_exclude_from ^/usr/lib/libVkLayer_chuds_fg\\.so$

%description
Generates extra frames between a game's own (optical flow on the GPU, x2 to
x8 or adaptive, interpolation or extrapolation) and upscales, as an implicit
Vulkan layer: native Vulkan games and Direct3D games under Proton (DXVK,
VKD3D-Proton). Inert until turned on (control panel chuds-fg-gui, or
CHUDS_FG=1); games protected by an anti-cheat are left alone.

%prep
%autosetup -n Chuds_fg-%{version}

%build
# Plain cmake rather than %%cmake: Fedora's and openSUSE's macros differ
# (build directory, working directory afterwards).
cmake -S . -B build64 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=%{_prefix} \
      -DCMAKE_C_FLAGS="%{optflags}" -DCMAKE_CXX_FLAGS="%{optflags}" \
      -DCHUDS_FG_BUILD_DEMO=OFF -DCHUDS_FG_BUILD_TESTS=OFF -DCHUDS_FG_BUILD_OFFLINE=OFF \
      -DCHUDS_FG_STATIC_RUNTIME=ON -DCHUDS_FG_INSTALL_LIBDIR=%{_lib}
cmake --build build64 %{?_smp_mflags}
%ifarch x86_64
%if %{with lib32}
# (no %%optflags: they carry -m64; -m32 comes from CHUDS_FG_32BIT)
cmake -S . -B build32 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=%{_prefix} \
      -DCHUDS_FG_32BIT=ON -DCHUDS_FG_STATIC_RUNTIME=ON -DCHUDS_FG_INSTALL_LIBDIR=lib
cmake --build build32 %{?_smp_mflags}
%endif
%endif

%install
DESTDIR=%{buildroot} cmake --install build64
%ifarch x86_64
%if %{with lib32}
DESTDIR=%{buildroot} cmake --install build32
%endif
%endif

%check
# The manifests name the installed libraries.
grep -q '"library_path": "%{_libdir}/libVkLayer_chuds_fg.so"' \
  %{buildroot}%{_datadir}/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json

%post
echo "chuds-fg: Steam, Heroic, Lutris or Bottles installed as a Flatpak? Run once, as your user:"
echo "    chuds-fg --sandboxes"

%files
%license LICENSE
%doc README.md
%{_bindir}/chuds-fg
%{_bindir}/chuds-fg-gui
%{_libdir}/libVkLayer_chuds_fg.so
%ifarch x86_64
%if %{with lib32}
%{_prefix}/lib/libVkLayer_chuds_fg.so
%{_datadir}/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg_32.json
%endif
%endif
%{_datadir}/vulkan/implicit_layer.d/VK_LAYER_CHUDS_fg.json
%{_datadir}/applications/chuds-fg.desktop
%{_datadir}/chuds-fg/

%changelog
* Mon Oct 05 2026 Bdexez <elian.marzari@epitech.eu> - 0.5.6-1
- New upstream release 0.5.6

* Thu Oct 01 2026 Bdexez <elian.marzari@epitech.eu> - 0.5.5-1
- Source package (COPR, OBS)
