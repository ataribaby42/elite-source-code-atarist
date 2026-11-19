#!/bin/sh
# Linux counterpart of build_amiga.bat. Persistent default options live here;
# anything on the command line overrides them, last occurrence winning.
# "all" builds every delivered image: one call each, named by its outputname.
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build="$here/src_amiga/build.sh"
set -e
build_image() {
    "$build" noprotect=yes commander=default laser=singlebeam scannerlogo=no fastdraw=yes "$@"
}

if [ "${1-}" != all ]; then
    build_image outputname=ELITE altgfx=no display=pal "$@"
    build_image outputname=ELITE_ALT altgfx=yes display=pal "$@"
    exit
fi

shift
# Keep user options as an argument vector. Each release entry still owns its
# output name and display, as before; only double-scan entries force CPU.
release_image() {
    image_name=$1
    image_alt=$2
    image_frame=$3
    image_display=$4
    shift 4
    case $image_display in
        dbl*) build_image frametime=no "$@" "outputname=$image_name" "altgfx=$image_alt" "frame=$image_frame" "display=$image_display" cpu=68020 ;;
        *) build_image frametime=no "$@" "outputname=$image_name" "altgfx=$image_alt" "frame=$image_frame" "display=$image_display" ;;
    esac
}
release_image ELITE                         no  yes pal            "$@"
release_image ELITE.WIDE.PAL                no  no  pal            "$@"
release_image ELITE.WIDE.NTSC               no  no  ntsc           "$@"
release_image ELITE.WIDE.PAL-HIRES          no  no  pal-hires      "$@"
release_image ELITE.WIDE.NTSC-HIRES         no  no  ntsc-hires     "$@"
release_image ELITE.WIDE.PAL-HIRESLACE      no  no  pal-hireslace  "$@"
release_image ELITE.WIDE.NTSC-HIRESLACE     no  no  ntsc-hireslace "$@"
release_image ELITE.WIDE.DBLPAL-HIRES       no  no  dblpal-hires   "$@"
release_image ELITE.WIDE.DBLNTSC-HIRES      no  no  dblntsc-hires  "$@"
release_image ELITE_ALT                     yes yes pal            "$@"
release_image ELITE_ALT.WIDE.PAL            yes no  pal            "$@"
release_image ELITE_ALT.WIDE.NTSC           yes no  ntsc           "$@"
release_image ELITE_ALT.WIDE.PAL-HIRES      yes no  pal-hires      "$@"
release_image ELITE_ALT.WIDE.NTSC-HIRES     yes no  ntsc-hires     "$@"
release_image ELITE_ALT.WIDE.PAL-HIRESLACE  yes no  pal-hireslace  "$@"
release_image ELITE_ALT.WIDE.NTSC-HIRESLACE yes no  ntsc-hireslace "$@"
release_image ELITE_ALT.WIDE.DBLPAL-HIRES   yes no  dblpal-hires   "$@"
release_image ELITE_ALT.WIDE.DBLNTSC-HIRES  yes no  dblntsc-hires  "$@"
