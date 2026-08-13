#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

sudo apt-get update

sudo apt-get install -y build-essential m4 tcsh csh libx11-dev tcl-dev tk-dev

sudo apt-get install -y git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool magic --field git-url) magic
cd magic
git checkout $(python3 ${src_path}/_tools.py --tool magic --field git-commit)

# Ubuntu 26.04's glibc removed the legacy System V <termio.h>. Migrate Magic's
# SYSV terminal code to the equivalent POSIX termios API: swap the header (and
# pull in <sys/ioctl.h> for ioctl()), the struct, and the TC*A ioctl requests.
grep -rl '#include <termio.h>' . | xargs -r sed -i \
    's|#include <termio.h>|#include <termios.h>\n#include <sys/ioctl.h>|'
grep -rlE '\bstruct termio\b|\bTC[GS]ETA' . | xargs -r sed -i -E \
    -e 's/\bstruct termio\b/struct termios/g' \
    -e 's/\bTCGETA\b/TCGETS/g' \
    -e 's/\bTCSETAF\b/TCSETSF/g' \
    -e 's/\bTCSETAW\b/TCSETSW/g' \
    -e 's/\bTCSETA\b/TCSETS/g'

# GCC 15 (Ubuntu 26.04) defaults to C23, where `bool` is a keyword and Magic's
# `typedef unsigned char bool;` no longer compiles. Magic's configure ignores
# $CFLAGS from the environment, so fold -std=gnu17 into $CC to force C17 on
# every compile.
LD_FLAGS=-shared CC="${CC:-gcc} -std=gnu17" ./configure ${PREFIX:+--prefix="$PREFIX"}
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install
