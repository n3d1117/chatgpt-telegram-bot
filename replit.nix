{pkgs}: {
  deps = [
    pkgs.rustc
    pkgs.libiconv
    pkgs.cargo
    pkgs.ffmpeg-full
    pkgs.inetutils
  ];
}
