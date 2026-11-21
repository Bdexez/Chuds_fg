# chuds-fg for Nix / NixOS: the layer (and, with pkgsi686Linux, the
# 32-bit one), the CLI and the control panel. See flake.nix at the repository
# root: `nix build`, `nix profile install`, or the NixOS module.
{ lib
, stdenv
, cmake
, shaderc
, vulkan-headers
, python3
, gtk4
, libadwaita
, gobject-introspection
, wrapGAppsHook4
, makeWrapper
, bash
, coreutils
, gawk
, gnugrep
, gnused
, procps
, vulkan-tools
, withPanel ? true
}:

stdenv.mkDerivation {
  pname = "chuds-fg";
  version = let m = builtins.match ".*project\\(chuds_fg VERSION ([0-9.]+).*"
                      (builtins.readFile ../../CMakeLists.txt);
            in builtins.head m;

  src = lib.cleanSourceWith {
    src = ../..;
    filter = path: type:
      let base = baseNameOf path; in
      !(lib.hasPrefix "build" base || base == "dist" || base == "result" || base == ".git");
  };

  nativeBuildInputs = [ cmake shaderc makeWrapper ]
    ++ lib.optionals withPanel [ wrapGAppsHook4 gobject-introspection ];
  buildInputs = [ vulkan-headers ]
    ++ lib.optionals withPanel [ gtk4 libadwaita (python3.withPackages (p: [ p.pygobject3 ])) ];

  cmakeFlags = [
    "-DCHUDS_FG_BUILD_TESTS=OFF"
    "-DCHUDS_FG_BUILD_DEMO=OFF"
    "-DCHUDS_FG_BUILD_OFFLINE=OFF"
    "-DCHUDS_FG_BUILD_CAPTURE=OFF"
    # A game in the Steam runtime (or an FHS environment) may bring an older
    # libstdc++ than the one of the store: the layer carries its own.
    "-DCHUDS_FG_STATIC_RUNTIME=ON"
  ] ++ lib.optional stdenv.hostPlatform.is32bit "-DCHUDS_FG_32BIT=ON";

  # The panel is wrapped by wrapGAppsHook4 (GTK 4 typelibs); the CLI gets the
  # tools it calls.
  dontWrapGApps = true;
  postFixup = lib.optionalString (!stdenv.hostPlatform.is32bit) ''
    wrapProgram $out/bin/chuds-fg \
      --prefix PATH : ${lib.makeBinPath [ bash coreutils gawk gnugrep gnused procps vulkan-tools ]}
  '' + lib.optionalString withPanel ''
    wrapProgram $out/bin/chuds-fg-gui "''${gappsWrapperArgs[@]}" \
      --prefix PATH : ${lib.makeBinPath [ (python3.withPackages (p: [ p.pygobject3 ])) procps ]}
  '' + lib.optionalString (!withPanel) ''
    rm -f $out/bin/chuds-fg-gui $out/share/applications/chuds-fg.desktop
  '' + lib.optionalString stdenv.hostPlatform.is32bit ''
    # Beside the 64-bit package in one profile: only the layer, its manifest
    # and its profiles (identical files do not collide).
    rm -rf $out/bin $out/share/applications $out/share/chuds-fg/options_ui.json $out/share/chuds-fg/flatpak.sh
  '';

  meta = {
    description = "Frame generation for Vulkan games (optical flow, x2 to x8) as an implicit Vulkan layer";
    homepage = "https://github.com/Bdexez/Chuds_fg";
    license = lib.licenses.unfree;  # proprietary (LICENSE); the flake allows it for itself
    platforms = [ "x86_64-linux" "aarch64-linux" "i686-linux" ];
    mainProgram = "chuds-fg";
  };
}
