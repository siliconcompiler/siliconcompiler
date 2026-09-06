#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

# Install prerequisites only when they are missing
. "${src_path}/_prereqs.sh"

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

install_prereqs git perl python3 make autoconf g++ flex bison ccache
install_prereqs libgoogle-perftools-dev numactl perl-doc help2man
install_prereqs libfl2
install_prereqs libfl-dev
install_prereqs zlib1g zlib1g-dev
# Verilator 5.040 moved FST tracing to libfstwriter: the model verilator
# generates includes <lz4.h> and verilated.mk links -llz4, so --trace-fst
# needs lz4 wherever the generated code is compiled, not just here.
install_prereqs liblz4-1 liblz4-dev

install_prereqs git

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
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install

cd -
