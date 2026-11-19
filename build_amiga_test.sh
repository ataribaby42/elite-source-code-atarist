#!/bin/sh
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "${1-}" = all ]; then
    shift
    exec "$here/build_amiga.sh" all commander=max frametime=yes shadowcopy=counter "$@"
fi
exec "$here/build_amiga.sh" commander=max frametime=yes shadowcopy=counter "$@"
