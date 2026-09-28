#!/bin/sh
# shellcheck disable=SC2086  # the option strings are meant to split
# Linux counterpart of build_amiga.bat. Persistent default options live here;
# anything on the command line overrides them, last occurrence winning.
# "all" builds every delivered image: one call each, named by its outputname.
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build="$here/src_amiga/build.sh"
common="noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes"
test=$BUILD_AMIGA_TEST  # build_amiga_test.sh sets these; the command line still wins

set -e
if [ "$1" != all ]; then
    "$build" outputname=ELITE $common altgfx=no display=pal $test "$@"
    "$build" outputname=ELITE_ALT $common altgfx=yes display=pal $test "$@"
    exit
fi

shift
common="$common frametime=no $test $*"  # extra options apply to every image, which keeps its own name and display
"$build" $common outputname=ELITE                         altgfx=no  frame=yes display=pal
"$build" $common outputname=ELITE.WIDE.PAL                altgfx=no  frame=no  display=pal
"$build" $common outputname=ELITE.WIDE.NTSC               altgfx=no  frame=no  display=ntsc
"$build" $common outputname=ELITE.WIDE.PAL-HIRES          altgfx=no  frame=no  display=pal-hires
"$build" $common outputname=ELITE.WIDE.NTSC-HIRES         altgfx=no  frame=no  display=ntsc-hires
"$build" $common outputname=ELITE.WIDE.PAL-HIRESLACE      altgfx=no  frame=no  display=pal-hireslace
"$build" $common outputname=ELITE.WIDE.NTSC-HIRESLACE     altgfx=no  frame=no  display=ntsc-hireslace
"$build" $common outputname=ELITE.WIDE.DBLPAL-HIRES       altgfx=no  frame=no  display=dblpal-hires cpu=68020
"$build" $common outputname=ELITE.WIDE.DBLNTSC-HIRES      altgfx=no  frame=no  display=dblntsc-hires cpu=68020
"$build" $common outputname=ELITE_ALT                     altgfx=yes frame=yes display=pal
"$build" $common outputname=ELITE_ALT.WIDE.PAL            altgfx=yes frame=no  display=pal
"$build" $common outputname=ELITE_ALT.WIDE.NTSC           altgfx=yes frame=no  display=ntsc
"$build" $common outputname=ELITE_ALT.WIDE.PAL-HIRES      altgfx=yes frame=no  display=pal-hires
"$build" $common outputname=ELITE_ALT.WIDE.NTSC-HIRES     altgfx=yes frame=no  display=ntsc-hires
"$build" $common outputname=ELITE_ALT.WIDE.PAL-HIRESLACE  altgfx=yes frame=no  display=pal-hireslace
"$build" $common outputname=ELITE_ALT.WIDE.NTSC-HIRESLACE altgfx=yes frame=no  display=ntsc-hireslace
"$build" $common outputname=ELITE_ALT.WIDE.DBLPAL-HIRES   altgfx=yes frame=no  display=dblpal-hires cpu=68020
"$build" $common outputname=ELITE_ALT.WIDE.DBLNTSC-HIRES  altgfx=yes frame=no  display=dblntsc-hires cpu=68020
