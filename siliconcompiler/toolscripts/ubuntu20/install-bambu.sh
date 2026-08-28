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
    gcc-8 gcc-8-multilib g++-8 g++-8-multilib \
    llvm-8 llvm-8-dev libllvm8 \
    gfortran-8 gfortran-8-multilib \
    clang-8 libclang-8-dev

# bambu's MDPI simulation runtime is built 32-bit, by whichever compiler is the
# distribution default -- not by the versioned gcc-N/g++-N pinned above. So it
# needs the unversioned multilib metapackages, which track that default:
#
#   gcc-multilib  ships /usr/include/asm, the unprefixed compatibility symlink
#                 the gcc-N-multilib packages do not provide. Without it:
#                   linux/errno.h:1:10: fatal error: 'asm/errno.h' file not found
#   g++-multilib  ships the 32-bit libstdc++ headers. Without it:
#                   c++/13/cstdio:41:10: fatal error: 'bits/c++config.h' file not found
#
# Pinning g++-11-multilib is not enough on a distribution whose default is newer
# (ubuntu24 defaults to 13), and only "bambu --simulate" fails -- well after
# synthesis has already succeeded.
install_prereqs gcc-multilib g++-multilib

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

../configure --enable-release --disable-flopoco --with-opt-level=2 $args
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install

cd -

if [ -z ${PREFIX} ]; then
    echo "Please add \"export PATH="/opt/panda/bin:\$PATH"\" to your .bashrc"
fi
