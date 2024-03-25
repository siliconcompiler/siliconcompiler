#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

# Install core dependencies.
sudo apt-get install -y build-essential gcc g++ make cmake automake autoconf bison flex git libblas-dev \
    liblapack-dev liblapack64-dev libfftw3-dev libsuitesparse-dev libopenmpi-dev libboost-all-dev \
    libnetcdf-dev libmatio-dev gfortran libfl-dev libtool python3-venv

mkdir -p deps
cd deps

if [ -z ${PREFIX} ]; then
    PREFIX=~/.local
fi

# Install CMAKE
python3 -m venv .xyce --clear
. .xyce/bin/activate
python3 -m pip install cmake>=3.23.0

# Download Trilinos.
## Version specified in: https://github.com/Xyce/Xyce/blob/master/INSTALL.md#building-trilinos
trilinos_version=14-4-0
wget https://github.com/trilinos/Trilinos/archive/refs/tags/trilinos-release-${trilinos_version}.tar.gz -O trilinos.tar.gz
mkdir -p trilinos
tar --strip-components=1 -xf trilinos.tar.gz -C trilinos

# Download Xyce.
xyce_version=$(python3 ${src_path}/_tools.py --tool xyce --field version)
wget https://github.com/Xyce/Xyce/archive/refs/tags/Release-${xyce_version}.tar.gz -O xyce.tar.gz
mkdir -p xyce
tar --strip-components=1 -xf xyce.tar.gz -C xyce

cd xyce

# Build Trilinos
mkdir trilinos-build
cd trilinos-build
cmake \
    -D CMAKE_INSTALL_PREFIX=$PREFIX/trilinos \
    -D AMD_LIBRARY_DIRS="/usr/lib" \
    -D TPL_AMD_INCLUDE_DIRS="/usr/include/suitesparse" \
    -C ../cmake/trilinos/trilinos-base.cmake \
    ../../trilinos
cmake --build . -j$(nproc) -t install

cd ..

# Build Xyce
mkdir xyce-build
cd xyce-build

cmake \
    -D CMAKE_INSTALL_PREFIX=$PREFIX \
    -D Trilinos_ROOT=$PREFIX/trilinos \
    -D BUILD_SHARED_LIBS=ON \
    ..

cmake --build . -j$(nproc)
cmake --build . -j$(nproc) --target xycecinterface
sudo -E PATH="$PATH" make install
