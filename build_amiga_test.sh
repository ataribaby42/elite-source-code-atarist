#!/bin/sh
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD_AMIGA_TEST="commander=max frametime=yes shadowcopy=counter" exec "$here/build_amiga.sh" "$@"
