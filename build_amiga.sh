#!/bin/sh
# shellcheck disable=SC2086  # the option strings are meant to split
# Linux counterpart of build_amiga.bat. Persistent default options live here;
# anything on the command line overrides them, last occurrence winning.
# "all" builds every delivered image: one call each, named by its outputname.
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build="$here/src_amiga/build.sh"
common="noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no"

if [ "$1" != all ]; then
    exec "$build" $common frame=no "$@"
fi

set -e
"$build" $common outputname=ELITE                         altgfx=no  frame=yes display=pal            cpu=68000
"$build" $common outputname=ELITE.WIDE.PAL                altgfx=no  frame=no  display=pal            cpu=68000
"$build" $common outputname=ELITE.WIDE.NTSC               altgfx=no  frame=no  display=ntsc           cpu=68000
"$build" $common outputname=ELITE.WIDE.PAL-HIRES          altgfx=no  frame=no  display=pal-hires      cpu=68020
"$build" $common outputname=ELITE.WIDE.NTSC-HIRES         altgfx=no  frame=no  display=ntsc-hires     cpu=68020
"$build" $common outputname=ELITE.WIDE.PAL-HIRESLACE      altgfx=no  frame=no  display=pal-hireslace  cpu=68020
"$build" $common outputname=ELITE.WIDE.NTSC-HIRESLACE     altgfx=no  frame=no  display=ntsc-hireslace cpu=68020
"$build" $common outputname=ELITE_ALT                     altgfx=yes frame=yes display=pal            cpu=68000
"$build" $common outputname=ELITE_ALT.WIDE.PAL            altgfx=yes frame=no  display=pal            cpu=68000
"$build" $common outputname=ELITE_ALT.WIDE.NTSC           altgfx=yes frame=no  display=ntsc           cpu=68000
"$build" $common outputname=ELITE_ALT.WIDE.PAL-HIRES      altgfx=yes frame=no  display=pal-hires      cpu=68020
"$build" $common outputname=ELITE_ALT.WIDE.NTSC-HIRES     altgfx=yes frame=no  display=ntsc-hires     cpu=68020
"$build" $common outputname=ELITE_ALT.WIDE.PAL-HIRESLACE  altgfx=yes frame=no  display=pal-hireslace  cpu=68020
"$build" $common outputname=ELITE_ALT.WIDE.NTSC-HIRESLACE altgfx=yes frame=no  display=ntsc-hireslace cpu=68020
