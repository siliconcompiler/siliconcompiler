#!/bin/bash

# Builds bambu against a privately unpacked clang 16.
#
# bambu's newest supported front end is clang 16 -- etc/macros stops at
# clang_version16.m4, on the release tag and on main alike -- and ubuntu26
# cannot supply one from a package:
#
#   * the archive starts at clang-17
#   * apt.llvm.org publishes nothing older than llvm-toolchain-resolute-21
#   * the jammy and noble llvm-16 packages will not install, because libllvm16
#     depends on libxml2 (>= 2.7.4) and 26.04 renamed the runtime library to
#     libxml2-16 (libxml2.so.16). Nothing provides libxml2.so.2 any more, so
#     those binaries could not run even if apt were forced past the metadata.
#
# The upstream LLVM release tarball is the way out: it is built without libxml2
# and needs only libm, libz, libzstd, libtinfo.so.6, libstdc++, libgcc_s and
# libc, all of which 26.04 has. So it is unpacked into the install prefix and
# handed to configure, and clang 16 stays off PATH where it cannot shadow the
# LLVM 19 tools the SODA flow drives.

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
    graphviz make libsuitesparse-dev libglpk-dev libgmp-dev \
    libfl-dev
install_prereqs \
    gcc-11 gcc-11-multilib g++-11 g++-11-multilib

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
# (ubuntu26 defaults to 15), and only "bambu --simulate" fails -- well after
# synthesis has already succeeded. clang 16's own -m32 support check in
# configure needs these too.
install_prereqs gcc-multilib g++-multilib

install_prereqs git build-essential wget xz-utils

if [ ! -z ${PREFIX} ]; then
    install_dir="$PREFIX"
else
    install_dir=/opt/panda
    SUDO_INSTALL=sudo

    $SUDO_INSTALL mkdir -p "${install_dir}"
    $SUDO_INSTALL chown $USER:$USER "${install_dir}"
fi
args=--prefix="${install_dir}"

# 16.0.4 is the newest LLVM 16 with an x86_64 linux tarball: 16.0.5 and 16.0.6
# published aarch64 and ppc64le builds only, and 16.0.0's is the older
# ubuntu-18.04 build, which wants libtinfo.so.5.
clang_version=16.0.4
clang_dir="${install_dir}/clang-16"

mkdir -p deps
cd deps

# ~6 GB unpacked, most of it the static libclang/libLLVM archives. It has to
# stay next to the built bambu, which invokes these binaries at run time.
if [ ! -x "${clang_dir}/bin/clang" ]; then
    wget --no-verbose -O clang16.tar.xz \
        "https://github.com/llvm/llvm-project/releases/download/llvmorg-${clang_version}/clang+llvm-${clang_version}-x86_64-linux-gnu-ubuntu-22.04.tar.xz"
    mkdir -p "${clang_dir}"
    tar -xf clang16.tar.xz -C "${clang_dir}" --strip-components=1
    rm clang16.tar.xz
fi

# ubuntu26's libstdc++ 15 headers no longer pull <cstdint> in transitively, so
# the LLVM 16 headers stop compiling where they use uint64_t:
#   llvm/ADT/SmallVector.h:109:62: error: use of undeclared identifier 'uint64_t'
# That breaks configure's clang plugin probe and, after it, the real plugins in
# etc/clang_plugin -- which are what bambu reads its inputs with, so there is no
# usable front end without them. configure hardcodes the flags it hands the
# plugin compiler (EXTRA_CLANG_OPTIONS is only ever empty or the old-ABI define),
# so the header goes in through clang++'s own default config file instead.
# clang++ only: <cstdint> is not a C header, and clang compiles C here.
printf -- '-include cstdint\n' > "${clang_dir}/bin/clang++.cfg"

# clang++ takes libstdc++ from the highest numbered GCC installation under
# /usr/lib/gcc/<triple>/ and never falls back, which on a rolling release cuts
# both ways. The prerequisites above already drag in gcc-16 -- libboost-all-dev
# pulls mpi-default-dev, which pulls gfortran and with it libgcc-16-dev -- so
# this clang 16 selects a GCC 16 whose libstdc++ it is three years too old to
# parse:
#
#   /usr/include/c++/16/bits/stl_iterator.h:1337:19: error: member access into
#       incomplete type 'const __normal_iterator<const CharSourceRange *, ...>'
#
# and if libstdc++-16-dev is not installed beside libgcc-16-dev it finds no C++
# standard library at all. configure discards the stderr of its plugin probe, so
# either way the only thing it reports is
#
#   checking ... plugin_test.o -fPIC -shared -o plugin_test.so ... no...
#       Package libclang-16.0-dev missing?
#   configure: error: "gcc with support to -m32 and plugin not found"
#
# naming a package this script deliberately does not use. Installing the newest
# libstdc++ is the wrong repair -- it answers the second failure with the first.
# Pin instead: walk the installed GCCs newest first and keep the first one this
# clang can actually compile clang's own headers against. That is the exact
# thing configure is about to do, so a pass here is a pass there.
probe_cpp="${PWD}/clang16_gcc_probe.cpp"
printf '#include "clang/Basic/Diagnostic.h"\n' > "${probe_cpp}"
clang_gcc_dir=
for candidate in $(ls -d /usr/lib/gcc/*/[0-9]* 2> /dev/null | sort -V -r); do
    if "${clang_dir}/bin/clang++" --gcc-install-dir="${candidate}" \
            -I"${clang_dir}/include" -std=c++17 -fsyntax-only "${probe_cpp}" 2> /dev/null; then
        clang_gcc_dir="${candidate}"
        break
    fi
done
rm -f "${probe_cpp}"

if [ -n "${clang_gcc_dir}" ]; then
    echo "clang 16 will use the libstdc++ from ${clang_gcc_dir}"
    printf -- '--gcc-install-dir=%s\n' "${clang_gcc_dir}" >> "${clang_dir}/bin/clang++.cfg"
else
    echo "WARNING: no installed GCC provides a libstdc++ that clang 16 can compile" >&2
    echo "         against. configure will report the clang plugin as unsupported." >&2
    echo "         Installing libstdc++-15-dev usually resolves this." >&2
fi

git clone $(python3 ${src_path}/_tools.py --tool bambu --field git-url) bambu
cd bambu
git checkout $(python3 ${src_path}/_tools.py --tool bambu --field git-commit)
git submodule update --init --recursive

make -f Makefile.init

mkdir obj
cd obj

# --with-clang16 takes the unsuffixed driver, not clang-16: the macro derives
# the rest of the toolchain from that basename with sed, so bin/clang gets it
# llvm-config, clang-cpp, clang++, llvm-link and opt, while bin/clang-16 would
# send it looking for an llvm-config-16 the tarball does not have.
CC=$(which gcc-11) CXX=$(which g++-11) ../configure --enable-release --disable-flopoco \
    --with-opt-level=2 --with-clang16="${clang_dir}/bin/clang" $args
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install

cd -

if [ -z ${PREFIX} ]; then
    echo "Please add \"export PATH="/opt/panda/bin:\$PATH"\" to your .bashrc"
fi
