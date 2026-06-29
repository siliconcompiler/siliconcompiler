#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo apt-get update

sudo apt-get install -y build-essential make curl libdwarf-dev libdw-dev

sudo apt-get install -y git

mkdir -p deps
cd deps

python3 -m venv .vcd2fst --clear
. .vcd2fst/bin/activate
python3 -m pip install cmake==3.31.6

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

if [ ! -z ${PREFIX} ]; then
    cmake_args="-DCMAKE_INSTALL_PREFIX=$PREFIX"
fi

git clone $(python3 ${src_path}/_tools.py --tool vcd2fst --field git-url) vcd2fst
cd vcd2fst
git checkout $(python3 ${src_path}/_tools.py --tool vcd2fst --field git-commit)
git submodule update --init --recursive

mkdir -p build
cd build
cmake .. $cmake_args -DCMAKE_BUILD_TYPE=Release
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL mkdir -p $PREFIX/bin
$SUDO_INSTALL cp vcd2fst $PREFIX/bin

cd -
