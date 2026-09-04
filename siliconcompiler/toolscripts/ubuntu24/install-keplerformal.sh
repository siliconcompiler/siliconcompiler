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

install_prereqs build-essential libfl-dev

# From: https://github.com/keplertech/kepler-formal/blob/ea6b0ce62f6f8fd2327e79913a07c74a3210551d/README.md
install_prereqs g++ libboost-dev python3-dev capnproto libcapnp-dev libtbb-dev \
    pkg-config bison flex doxygen libspdlog-dev libfmt-dev libboost-iostreams-dev zlib1g-dev

install_prereqs git

mkdir -p deps
cd deps

python3 -m venv .keplerformal --clear
. .keplerformal/bin/activate
python3 -m pip install cmake==3.31.6

git clone $(python3 ${src_path}/_tools.py --tool keplerformal --field git-url) keplerformal
cd keplerformal
git checkout $(python3 ${src_path}/_tools.py --tool keplerformal --field git-commit)
git submodule update --init --recursive

cmake_args=""
if [ ! -z ${PREFIX} ]; then
    cmake_args="-DCMAKE_INSTALL_PREFIX=$PREFIX"
fi

mkdir -p build
cd build

# Never -march=native here, whatever upstream's README suggests for a local
# build. This prefix gets shipped: it is what goes into the sc_tools container
# image, and it is what a shared sc-install prefix hands to other machines. The
# instruction set of whichever machine did the build is not a property any of
# those consumers share, and the failure is a SIGILL on the first wide
# instruction rather than anything diagnosable.
#
# It bit exactly that way: two consecutive image builds differed only in which
# runner compiled them, and the one that landed on an AVX-512 host produced a
# kepler-formal with 1533 zmm references that died with "Illegal instruction"
# on every test runner without AVX-512. The build before it, on a host without
# it, had none and ran everywhere.
#
# install-openroad.sh already settled the same question the same way, pinning
# -march=x86-64 for Qt and naming x86-64-v3 only where a file needs it.
cmake .. -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS_RELEASE="-Ofast -ffast-math -flto" \
    -DCMAKE_EXE_LINKER_FLAGS="-flto" \
	-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=TRUE \
    -DENABLE_UNIT_TESTS=OFF \
    $cmake_args
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install

cd -
