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

# Ubuntu 26.04 dropped the versioned libgnat-9 package; the gnat metapackage
# already pulls the matching libgnat runtime, so it is no longer listed here.
# Ubuntu 26.04 also defaults to LLVM 21, but GHDL v5.1.1 only supports up to
# LLVM 20, so install the versioned llvm-20 packages explicitly.
install_prereqs llvm-20-dev clang-20 gnat libz-dev

install_prereqs git build-essential

# GHDL's LLVM backend build invokes `clang++` (unversioned); provide it from the
# pinned clang-20 toolchain so it matches llvm-config-20.
sudo ln -sf "$(command -v clang++-20 || echo /usr/lib/llvm-20/bin/clang++)" /usr/local/bin/clang++

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool ghdl --field git-url) ghdl
cd ghdl
git checkout $(python3 ${src_path}/_tools.py --tool ghdl --field git-commit)

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

./configure --with-llvm-config=llvm-config-20 $args
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install
cd -
