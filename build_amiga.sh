#!/bin/sh
# shellcheck disable=SC2086  # the option strings are meant to split
# Linux counterpart of build_amiga.bat. Persistent default options live here;
# anything on the command line overrides them, last occurrence winning.
# "all" builds every delivered image: one call each, named by its outputname.
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build="$here/src_amiga/build.sh"
common="noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes"

if [ "$1" != all ]; then
    exec "$build" $common frame=no "$@"
fi

set -e
shift
common="$common $*"  # extra options apply to every image, which keeps its own name and display
"$build" $common outputname=ELITE                         altgfx=no  frame=yes display=pal
"$build" $common outputname=ELITE.WIDE.PAL                altgfx=no  frame=no  display=pal            frametime=yes
"$build" $common outputname=ELITE.WIDE.NTSC               altgfx=no  frame=no  display=ntsc           frametime=yes
"$build" $common outputname=ELITE.WIDE.PAL-HIRES          altgfx=no  frame=no  display=pal-hires      frametime=yes
"$build" $common outputname=ELITE.WIDE.NTSC-HIRES         altgfx=no  frame=no  display=ntsc-hires     frametime=yes
"$build" $common outputname=ELITE.WIDE.PAL-HIRESLACE      altgfx=no  frame=no  display=pal-hireslace  frametime=yes
"$build" $common outputname=ELITE.WIDE.NTSC-HIRESLACE     altgfx=no  frame=no  display=ntsc-hireslace frametime=yes
"$build" $common outputname=ELITE_ALT                     altgfx=yes frame=yes display=pal
"$build" $common outputname=ELITE_ALT.WIDE.PAL            altgfx=yes frame=no  display=pal            frametime=yes
"$build" $common outputname=ELITE_ALT.WIDE.NTSC           altgfx=yes frame=no  display=ntsc           frametime=yes
"$build" $common outputname=ELITE_ALT.WIDE.PAL-HIRES      altgfx=yes frame=no  display=pal-hires      frametime=yes
"$build" $common outputname=ELITE_ALT.WIDE.NTSC-HIRES     altgfx=yes frame=no  display=ntsc-hires     frametime=yes
"$build" $common outputname=ELITE_ALT.WIDE.PAL-HIRESLACE  altgfx=yes frame=no  display=pal-hireslace  frametime=yes
"$build" $common outputname=ELITE_ALT.WIDE.NTSC-HIRESLACE altgfx=yes frame=no  display=ntsc-hireslace frametime=yes
