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

# From: https://github.com/YosysHQ/yosys/blob/f2c689403ace0637b7455bac8f1e8d4bc312e74f/README.md
sudo apt-get install -y build-essential clang bison flex \
	libreadline-dev gawk tcl-dev libffi-dev git libfl-dev \
	graphviz xdot pkg-config python3 libboost-system-dev \
	libboost-python-dev libboost-filesystem-dev zlib1g-dev

sudo apt-get install -y git

mkdir -p deps
cd deps

python3 -m venv .yosys --clear
. .yosys/bin/activate
python3 -m pip install cmake==3.31.6

git clone $(python3 ${src_path}/_tools.py --tool yosys --field git-url) yosys
cd yosys
git checkout $(python3 ${src_path}/_tools.py --tool yosys --field git-commit)
git submodule update --init --recursive

mkdir build
cd build

cmake -DCMAKE_BUILD_TYPE=Release \
    -D CMAKE_INSTALL_PREFIX="$PREFIX" \
	..

make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install

cd -
