#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo yum install -y gcc-gnat zlib-devel diffutils
sudo yum install -y git

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
sudo make install
cd -
