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

sudo apt-get install -y autoconf autoconf-archive automake libtool \
    libbdd-dev libboost-all-dev libmpc-dev libmpfr-dev \
    libxml2-dev liblzma-dev libmpfi-dev zlib1g-dev libicu-dev bison doxygen flex \
    graphviz iverilog verilator make libsuitesparse-dev libglpk-dev libgmp-dev \
    libfl-dev
sudo apt-get install -y \
    gcc-11 gcc-11-multilib g++-11 g++-11-multilib \
    llvm-11 llvm-11-dev libllvm11 \
    gfortran-10 gfortran-10-multilib \
    clang-11 libclang-11-dev

sudo apt-get install -y git build-essential

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
    SUDO_INSTALL=sudo

    sudo mkdir -p /opt/panda
    sudo chown $USER:$USER /opt/panda
fi

make -f Makefile.init

mkdir obj
cd obj

../configure --enable-release --disable-flopoco --with-opt-level=2 $args
make -j$(nproc)
$SUDO_INSTALL make install

cd -

if [ -z ${PREFIX} ]; then
    echo "Please add \"export PATH="/opt/panda/bin:\$PATH"\" to your .bashrc"
fi
