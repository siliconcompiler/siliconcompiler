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

# bambu decides whether it has a usable clang front end by compiling a plugin
# against clang's C++ API -- the only C++ compile in this build not done by the
# pinned g++ above. clang++ takes libstdc++ from the highest numbered GCC
# installation under /usr/lib/gcc/<triple>/, expects the headers in
# /usr/include/c++/<that version>, and never falls back to an older one. Two
# ways that goes wrong, both silent:
#
#   * a bare libgcc-N-dev arrives as some other package's dependency with no
#     libstdc++-N-dev beside it, leaving clang++ with no C++ standard library:
#         fatal error: 'type_traits' file not found
#   * the newest GCC is newer than this clang understands and its libstdc++
#     headers no longer parse -- what GCC 16 does to clang 16 on ubuntu26.
#
# Either way every gcc build keeps working, which is why configure's version and
# -m32 probes still pass, and configure throws the plugin probe's stderr away:
#
#   checking ... plugin_test.o -fPIC -shared -o plugin_test.so ... no...
#       Package libclang-8.0-dev missing?
#   configure: error: "gcc with support to -m32 and plugin not found"
#
# naming a package that is installed. So run the probe here, where the error is
# visible, on the same clang header the plugin pulls in -- and repair the case
# that is repairable from a package.
clang_cxx_probe() {
    echo '#include "clang/Basic/Diagnostic.h"' |
        clang++-8 -x c++ -std=c++17 -fsyntax-only \
            -I"$(llvm-config-8 --includedir)" - 2> /dev/null
}

if command -v clang++-8 > /dev/null 2>&1 &&
        command -v llvm-config-8 > /dev/null 2>&1 &&
        ! clang_cxx_probe; then
    clang_gcc=$(clang++-8 -v -x c++ /dev/null -fsyntax-only 2>&1 |
        sed -n 's#.*Selected GCC installation: *##p' | head -1)
    clang_gcc=${clang_gcc%/}
    clang_gcc=${clang_gcc##*/}
    clang_gcc=${clang_gcc%%.*}
    if [ -n "${clang_gcc}" ]; then
        install_prereqs "libstdc++-${clang_gcc}-dev"
    fi
    if ! clang_cxx_probe; then
        echo "WARNING: clang++-8 cannot compile clang's own C++ headers, so" >&2
        echo "         configure will report the clang plugin as unsupported." >&2
        echo "         It is using the libstdc++ from GCC ${clang_gcc}; if that is" >&2
        echo "         newer than clang 8 supports, removing that GCC's -dev" >&2
        echo "         packages makes clang fall back to the next one down." >&2
    fi
fi

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
