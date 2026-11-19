#!/bin/sh
# Linux entry point for the Amiga build: it finds an interpreter, runs build.py
# once per display named, and leaves the rest to it.
#
#   build.sh [option...]              PAL then NTSC
#   build.sh display=pal [option...]  one build; see build.py for display names
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
# Consume the original arguments once, appending forwarded arguments intact.
# Quoted "$@" preserves spaces, wildcard characters and empty values in POSIX sh.
remaining=$#
while [ "$remaining" -gt 0 ]; do
    argument=$1
    shift
    remaining=$((remaining - 1))
    case $argument in
        --python|--vasm|--vlink)
            if [ "$remaining" -eq 0 ] || [ -z "$1" ]; then
                echo "build.sh: $argument requires a path" >&2
                exit 1
            fi
            if [ "$argument" = --python ]; then
                python=$1
            else
                set -- "$@" "$argument" "$1"
            fi
            shift
            remaining=$((remaining - 1))
            ;;
        display=*) display=${argument#display=} ;;
        *) set -- "$@" "$argument" ;;
    esac
done

command -v "$python" >/dev/null 2>&1 ||
    { echo "build.sh: no $python on PATH" >&2; exit 1; }

case $display in
    ''|both)
        "$python" -B "$here/build.py" "$@" display=pal
        "$python" -B "$here/build.py" "$@" display=ntsc
        ;;
    *) "$python" -B "$here/build.py" "$@" "display=$display" ;;
esac
