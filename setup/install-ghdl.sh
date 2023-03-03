#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

sudo apt-get install -y gnat libgnat-7

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool ghdl --field git-url) ghdl
cd ghdl
git checkout $(python3 ${src_path}/_tools.py --tool ghdl --field git-commit)

./configure
make
sudo make install
cd -
