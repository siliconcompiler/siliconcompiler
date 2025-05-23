#!/bin/sh

set -ex

sudo apt-get install -y build-essential clang bison flex libreadline-dev \
                        gawk tcl-dev libffi-dev git mercurial graphviz   \
                        xdot pkg-config python3 libftdi-dev \
                        qtbase5-dev python3-dev libboost-all-dev cmake libeigen3-dev


sudo apt-get install -y git

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool nextpnr --field git-url) nextpnr
cd nextpnr
git checkout $(python3 ${src_path}/_tools.py --tool nextpnr --field git-commit)

args=
if [ ! -z ${PREFIX} ]; then
    args=-DCMAKE_INSTALL_PREFIX="$PREFIX"
fi

cmake -DARCH=ice40 $args .
make -j$(nproc)
$SUDO_INSTALL make install
cd -
