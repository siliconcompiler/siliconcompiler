#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo yum group install -y "Development Tools"
sudo yum install -y tcl-devel tk-devel git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool netgen --field git-url) netgen
cd netgen
git checkout $(python3 ${src_path}/_tools.py --tool netgen --field git-commit)

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

./configure $args
make -j$(nproc)
sudo make install
