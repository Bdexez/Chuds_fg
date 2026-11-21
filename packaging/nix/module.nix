# NixOS module: programs.chuds-fg.enable = true;
# The Vulkan loader finds implicit layers in $XDG_DATA_DIRS/vulkan: the
# package goes into the system profile with share/vulkan linked, and the
# 32-bit layer too (for 32-bit games, Steam's included).
self:
{ config, lib, pkgs, ... }:
let
  cfg = config.programs.chuds-fg;
in {
  options.programs.chuds-fg = {
    enable = lib.mkEnableOption "chuds-fg, frame generation for Vulkan games";
    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
      description = "The chuds-fg package.";
    };
    enable32Bit = lib.mkOption {
      type = lib.types.bool;
      default = pkgs.stdenv.hostPlatform.isx86_64;
      description = "Also install the 32-bit layer, for 32-bit games.";
    };
  };
  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ]
      ++ lib.optional cfg.enable32Bit self.packages.${pkgs.stdenv.hostPlatform.system}.layer32;
    environment.pathsToLink = [ "/share/vulkan" ];
  };
}
