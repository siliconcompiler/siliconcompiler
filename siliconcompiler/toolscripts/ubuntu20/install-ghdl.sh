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

sudo apt-get install -y gnat libgnat-9 libz-dev

sudo apt-get install -y git build-essential

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool ghdl --field git-url) ghdl
cd ghdl
git checkout $(python3 ${src_path}/_tools.py --tool ghdl --field git-commit)

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

./configure $args
make -j$(nproc)
$SUDO_INSTALL make install
cd -
