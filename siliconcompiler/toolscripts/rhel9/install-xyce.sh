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

mkdir -p deps
cd deps

if [ -z ${PREFIX} ]; then
    PREFIX=~/.local
fi

# Core dependencies. The 'devel' repository is disabled by default; enabling and
# disabling it is root-only work whose only purpose is the install between them,
# so the whole block is skipped when those packages are already present.
devel_pkgs="gcc gcc-c++ gcc-gfortran blas blas-devel \
    cmake lapack lapack-devel bison flex fftw-devel fftw \
    suitesparse suitesparse-devel autoconf automake libtool \
    git"
if prereqs_missing $devel_pkgs; then
    sudo dnf config-manager --set-enabled devel || true
    install_prereqs $devel_pkgs
    sudo dnf config-manager --set-disabled devel || true
fi

install_prereqs wget

# Download Trilinos.
## Version specified in: https://github.com/Xyce/Xyce/blob/master/INSTALL.md#building-trilinos
trilinos_version=14-4-0
wget https://github.com/trilinos/Trilinos/archive/refs/tags/trilinos-release-${trilinos_version}.tar.gz --no-verbose -O trilinos.tar.gz
mkdir -p trilinos
tar --strip-components=1 -xf trilinos.tar.gz -C trilinos

# Download Xyce.
git clone $(python3 ${src_path}/_tools.py --tool xyce --field git-url) xyce
cd xyce
git checkout $(python3 ${src_path}/_tools.py --tool xyce --field git-commit)

# Build Trilinos inside the Xyce tree (we are in deps/xyce) so both the -C cache
# file (xyce/cmake/...) and the Trilinos source (deps/trilinos, ../../trilinos)
# resolve correctly.
mkdir trilinos-build
cd trilinos-build
cmake \
    -D CMAKE_INSTALL_PREFIX="$PREFIX/trilinos" \
    -D AMD_LIBRARY_DIRS="/usr/lib" \
    -D TPL_AMD_INCLUDE_DIRS="/usr/include/suitesparse" \
    -C ../cmake/trilinos/trilinos-base.cmake \
    ../../trilinos
cmake --build . -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install

cd ..

# Build Xyce
mkdir xyce-build
cd xyce-build
cmake \
    -D CMAKE_INSTALL_PREFIX="$PREFIX" \
    -D Trilinos_ROOT=$PREFIX/trilinos \
    -D BUILD_SHARED_LIBS=ON \
    ..
cmake --build . -j${NPROC:-$(nproc)}
cmake --build . -j${NPROC:-$(nproc)} --target xycecinterface
$SUDO_INSTALL make install
cd -
