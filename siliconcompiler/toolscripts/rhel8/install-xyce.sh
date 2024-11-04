#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

mkdir -p deps
cd deps

if [ -z ${PREFIX} ]; then
    PREFIX=~/.local
fi

sudo dnf config-manager --set-enabled devel || true
# Install core dependencies.
sudo yum install -y gcc gcc-c++ gcc-gfortran blas blas-devel \
    cmake lapack lapack-devel bison flex fftw-devel fftw \
    suitesparse suitesparse-devel autoconf automake libtool \
    git
sudo dnf config-manager --set-disabled devel || true

# Download Trilinos.
## Version specified in: https://github.com/Xyce/Xyce/blob/master/INSTALL.md#building-trilinos
trilinos_version=14-4-0
wget https://github.com/trilinos/Trilinos/archive/refs/tags/trilinos-release-${trilinos_version}.tar.gz --no-verbose -O trilinos.tar.gz
mkdir -p trilinos
tar --strip-components=1 -xf trilinos.tar.gz -C trilinos

# Download Xyce.
xyce_version=$(python3 ${src_path}/_tools.py --tool xyce --field version)
wget https://xyce.sandia.gov/files/xyce/Xyce-${xyce_version}.tar.gz --no-verbose -O xyce.tar.gz
mkdir -p xyce
tar --strip-components=1 -xf xyce.tar.gz -C xyce
rm xyce.tar.gz
XYCE_DIR=$(realpath xyce)

# Build Trilinos
cd trilinos
mkdir build
cd build
cmake \
    -D CMAKE_INSTALL_PREFIX="$PREFIX/trilinos" \
    -D AMD_LIBRARY_DIRS="/usr/lib" \
    -D TPL_AMD_INCLUDE_DIRS="/usr/include/suitesparse" \
    -C "$XYCE_DIR/cmake/trilinos/trilinos-base.cmake" \
    ..
cmake --build . -j$(nproc) -t install
cd ../..

# Build Xyce
cd xyce
mkdir build
cd build
cmake \
    -D CMAKE_INSTALL_PREFIX="$PREFIX" \
    -D Trilinos_ROOT=$PREFIX/trilinos \
    -D BUILD_SHARED_LIBS=ON \
    ..
cmake --build . -j$(nproc)
cmake --build . -j$(nproc) --target xycecinterface
sudo make install
cd -
