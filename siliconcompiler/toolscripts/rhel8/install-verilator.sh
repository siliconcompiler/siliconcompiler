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

sudo yum group install -y "Development Tools"
sudo yum install -y git wget

mkdir -p deps
cd deps

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

wget https://ftp.wayne.edu/gnu/help2man/help2man-1.43.3.tar.gz
tar xvf help2man-1.43.3.tar.gz
cd help2man-1.43.3

./configure $args
make -j$(nproc)
$SUDO_INSTALL make install

cd ..

unset VERILATOR_ROOT

git clone $(python3 ${src_path}/_tools.py --tool verilator --field git-url) verilator
cd verilator
git checkout $(python3 ${src_path}/_tools.py --tool verilator --field git-commit)

autoconf

./configure $args
make -j$(nproc)
$SUDO_INSTALL make install

cd -
