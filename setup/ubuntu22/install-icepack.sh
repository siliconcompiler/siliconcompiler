#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

sudo apt-get install -y build-essential clang bison flex libreadline-dev \
                        gawk tcl-dev libffi-dev git mercurial graphviz   \
                        xdot pkg-config python3 libftdi-dev \
                        qtbase5-dev python3-dev libboost-all-dev cmake libeigen3-dev

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool icepack --field git-url) icepack
cd icepack
git checkout $(python3 ${src_path}/_tools.py --tool icepack --field git-commit)

make -j$(nproc)
sudo make install
cd -
