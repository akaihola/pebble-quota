{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = with pkgs; [
    pixman libpng SDL2 libpulseaudio glib alsa-lib zlib
    xvfb-run xorg-server xauth
  ];
  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (with pkgs; [
    pixman
    libpng
    SDL2
    libpulseaudio
    glib
    alsa-lib
    zlib
    stdenv.cc.cc.lib
  ]);
}
