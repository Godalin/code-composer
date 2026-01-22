{
  pkgs ? import <nixpkgs> { },
}:
pkgs.mkShell {
  packages = with pkgs; [
    ffmpeg
    fluidsynth
    timidity
    alda
    uv
  ];
}
