#!/bin/sh
# Linux entry point for the Amiga build: it finds an interpreter, runs build.py
# once per display named, and leaves the rest to it.
#
#   build.sh [option...]              PAL then NTSC
#   build.sh display=pal [option...]  one build; see build.py for the six
#                                     display names
#
#   --python PATH  interpreter to use (default: python3)
#   --vasm PATH    assembler override, passed to build.py
#   --vlink PATH   linker override, passed to build.py
#
# ELITE_VASM and ELITE_VLINK name a tool without the flag.
set -e

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

python=python3
display=
options=
tools=

while [ $# -gt 0 ]; do
    case $1 in
        --python) python=$2; shift 2 ;;
        --vasm) tools="$tools --vasm $2"; shift 2 ;;
        --vlink) tools="$tools --vlink $2"; shift 2 ;;
        display=*) display=${1#display=}; shift ;;
        *) options="$options $1"; shift ;;
    esac
done

command -v "$python" >/dev/null 2>&1 ||
    { echo "build.sh: no $python on PATH" >&2; exit 1; }

case $display in
    ''|both) screens='display=pal display=ntsc' ;;
    *) screens="display=$display" ;;
esac

for screen in $screens; do
    # shellcheck disable=SC2086
    "$python" -B "$here/build.py" $tools $options "$screen"
done
