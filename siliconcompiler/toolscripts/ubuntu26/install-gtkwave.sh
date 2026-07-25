#!/bin/sh

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

sudo apt-get install -y build-essential gperf libgtk-3-dev \
    libbz2-dev libjudy-dev liblzma-dev tcl-dev tk-dev autotools-dev \
    automake

sudo apt-get install -y git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool gtkwave --field git-url) gtkwave
cd gtkwave
git checkout $(python3 ${src_path}/_tools.py --tool gtkwave --field git-commit)

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

cd gtkwave3-gtk3

./autogen.sh
# GCC 14+ (Ubuntu 26.04) promotes -Wincompatible-pointer-types to a hard error,
# which breaks GTKWave's GTK3 callback casts. Downgrade it back to a warning.
CFLAGS="-Wno-error=incompatible-pointer-types -Wno-error=int-conversion" \
    ./configure --enable-gtk3 $args
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install
