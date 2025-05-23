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

sudo apt-get install -y git wget

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool vpr --field git-url) vpr
cd vpr
git checkout $(python3 ${src_path}/_tools.py --tool vpr --field git-commit)
git submodule update --init --recursive

./install_apt_packages.sh

args=
if [ ! -z ${PREFIX} ]; then
    args="-DCMAKE_INSTALL_PREFIX=$PREFIX"
fi

make CMAKE_PARAMS="$args -DWITH_PARMYS=OFF -DWITH_ABC=OFF -DYOSYS_F4PGA_PLUGINS=OFF" -j$(nproc)
cd build
$SUDO_INSTALL make install
