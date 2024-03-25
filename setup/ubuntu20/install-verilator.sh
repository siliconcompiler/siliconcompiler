#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

sudo apt-get install -y git perl python3 make autoconf g++ flex bison ccache
sudo apt-get install -y libgoogle-perftools-dev numactl perl-doc help2man
sudo apt-get install -y libfl2
sudo apt-get install -y libfl-dev
sudo apt-get install -y zlib1g zlib1g-dev

mkdir -p deps
cd deps

unset VERILATOR_ROOT

git clone $(python3 ${src_path}/_tools.py --tool verilator --field git-url) verilator
cd verilator
git checkout $(python3 ${src_path}/_tools.py --tool verilator --field git-commit)

autoconf

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

./configure $args
make -j$(nproc)
sudo make install

cd -
