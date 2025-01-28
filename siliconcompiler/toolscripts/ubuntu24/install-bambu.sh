#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo apt-get install -y autoconf autoconf-archive automake libtool \
    libbdd-dev libboost-all-dev libmpc-dev libmpfr-dev \
    libxml2-dev liblzma-dev libmpfi-dev zlib1g-dev libicu-dev bison doxygen flex \
    graphviz iverilog verilator make libsuitesparse-dev libglpk-dev libgmp-dev \
    libfl-dev
sudo apt-get install -y \
    gcc-11 gcc-11-multilib g++-11 g++-11-multilib \
    llvm-16 llvm-16-dev libllvm16 \
    clang-16 libclang-16-dev

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool bambu --field git-url) bambu
cd bambu
git checkout $(python3 ${src_path}/_tools.py --tool bambu --field git-commit)
git submodule update --init --recursive

if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
else
    args=--prefix=/opt/panda

    sudo mkdir -p /opt/panda
    sudo chown $USER:$USER /opt/panda
fi

make -f Makefile.init

mkdir obj
cd obj

CC=$(which gcc-11) CXX=$(which g++-11) ../configure --enable-release --disable-flopoco --with-opt-level=2 $args
make -j$(nproc)
make install

cd -

if [ -z ${PREFIX} ]; then
    echo "Please add \"export PATH="/opt/panda/bin:\$PATH"\" to your .bashrc"
fi
