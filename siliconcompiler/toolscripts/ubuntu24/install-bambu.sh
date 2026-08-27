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

install_prereqs autoconf autoconf-archive automake libtool \
    libbdd-dev libboost-all-dev libmpc-dev libmpfr-dev \
    libxml2-dev liblzma-dev libmpfi-dev zlib1g-dev libicu-dev bison doxygen flex \
    graphviz iverilog verilator make libsuitesparse-dev libglpk-dev libgmp-dev \
    libfl-dev
install_prereqs \
    gcc-11 gcc-11-multilib g++-11 g++-11-multilib \
    llvm-16 llvm-16-dev libllvm16 \
    clang-16 libclang-16-dev

# gcc-multilib ships /usr/include/asm, the unprefixed compatibility symlink that
# the versioned gcc-N-multilib packages do not provide. bambu's MDPI simulation
# runtime compiles against <linux/errno.h>, which includes <asm/errno.h> without
# the multiarch prefix, and builds it with a compiler that has no multiarch
# include path -- so without this, "bambu --simulate" fails with
#   /usr/include/linux/errno.h:1:10: fatal error: 'asm/errno.h' file not found
# and only that step fails, well after synthesis has succeeded.
install_prereqs gcc-multilib

install_prereqs git build-essential

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

    $SUDO_INSTALL mkdir -p /opt/panda
    $SUDO_INSTALL chown $USER:$USER /opt/panda
fi

make -f Makefile.init

mkdir obj
cd obj

CC=$(which gcc-11) CXX=$(which g++-11) ../configure --enable-release --disable-flopoco --with-opt-level=2 $args
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install

cd -

if [ -z ${PREFIX} ]; then
    echo "Please add \"export PATH="/opt/panda/bin:\$PATH"\" to your .bashrc"
fi
