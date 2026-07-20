#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

sudo apt-get update

# sby is pure python and drives yosys / yosys-smtbmc (installed separately); its
# 'click' dependency is bundled into the tool prefix below. The remaining packages
# build the bitwuzla SMT solver (the default sby engine) and its GMP/MPFR deps.
sudo apt-get install -y git python3 python3-pip build-essential cmake curl \
                        ninja-build pkg-config xz-utils m4 file

mkdir -p deps
cd deps

# --- SymbiYosys (sby) ---
git clone $(python3 ${src_path}/_tools.py --tool sby --field git-url) sby
cd sby
git checkout $(python3 ${src_path}/_tools.py --tool sby --field git-commit)
$SUDO_INSTALL make install PREFIX="$PREFIX"
cd -

# sby imports 'click' at runtime. The apt python3-click package installs outside
# $PREFIX and is not copied into the combined tool image, so bundle click next
# to sby_core.py (already on sby's sys.path) where it travels with $PREFIX and
# stays importable by whichever python ends up running sby.
$SUDO_INSTALL python3 -m pip install --target "$PREFIX/share/yosys/python3" "click==8.1.7"

# meson (>= 1.1) drives the bitwuzla build; apt's meson is too old on Ubuntu 22.
$SUDO_INSTALL python3 -m pip install --break-system-packages "meson>=1.1" 2>/dev/null || \
    $SUDO_INSTALL python3 -m pip install "meson>=1.1"

# bitwuzla needs GMP >= 6.3 and MPFR >= 4.2.1, newer than Ubuntu 22 ships, and
# both must live in $PREFIX so they travel with the tool image (only $PREFIX is
# copied, like click above). Build them from source into $PREFIX on every release
# for a uniform, self-contained result. '-std=gnu17' keeps GMP's configure probes
# valid under the C23 default of gcc >= 15. GMP/MPFR ship no pkg-config files, so
# write them for bitwuzla's meson to find the right versions.
prefix="${PREFIX:-/usr/local}"
$SUDO_INSTALL mkdir -p "$prefix/lib/pkgconfig"

curl -fL https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz -o gmp.tar.xz
tar xf gmp.tar.xz
cd gmp-6.3.0
./configure CC="gcc -std=gnu17" CXX="g++ -std=gnu++17" \
    --prefix="$prefix" --enable-static --enable-shared --enable-cxx
make -j"${NPROC:-$(nproc)}"
$SUDO_INSTALL make install
cd -
$SUDO_INSTALL tee "$prefix/lib/pkgconfig/gmp.pc" >/dev/null <<EOF
prefix=$prefix
libdir=\${prefix}/lib
includedir=\${prefix}/include
Name: GMP
Description: GNU MP
Version: 6.3.0
Libs: -L\${libdir} -lgmp
Cflags: -I\${includedir}
EOF

curl -fL https://ftp.gnu.org/gnu/mpfr/mpfr-4.2.2.tar.xz -o mpfr.tar.xz
tar xf mpfr.tar.xz
cd mpfr-4.2.2
./configure CC="gcc -std=gnu17" --prefix="$prefix" --with-gmp="$prefix" \
    --enable-static --enable-shared
make -j"${NPROC:-$(nproc)}"
$SUDO_INSTALL make install
cd -
$SUDO_INSTALL tee "$prefix/lib/pkgconfig/mpfr.pc" >/dev/null <<EOF
prefix=$prefix
libdir=\${prefix}/lib
includedir=\${prefix}/include
Name: MPFR
Description: GNU MPFR
Version: 4.2.2
Requires: gmp
Libs: -L\${libdir} -lmpfr
Cflags: -I\${includedir}
EOF

export PKG_CONFIG_PATH="$prefix/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export LD_LIBRARY_PATH="$prefix/lib:${LD_LIBRARY_PATH:-}"

# --- Bitwuzla (the SMT solver the default 'smtbmc bitwuzla' engine uses) ---
# Built here, not as its own tool, because the CI image build does not support
# chaining docker-depends (sby already depends on yosys). yosys >= 0.67 drives
# bitwuzla via its native '--lang' interface. Modern C++/meson build, so no
# compiler shims are needed; CaDiCaL + SymFPU are fetched by meson. Shared linking
# uses the GMP/MPFR shared libs above (a fully static binary would also need
# static libc/libstdc++, which the base image does not ship).
git clone $(python3 ${src_path}/_tools.py --tool bitwuzla --field git-url) bitwuzla
cd bitwuzla
git checkout $(python3 ${src_path}/_tools.py --tool bitwuzla --field git-commit)
meson setup build ${PREFIX:+--prefix "$PREFIX"} --buildtype=release -Ddefault_library=shared
ninja -C build -j"${NPROC:-$(nproc)}"
$SUDO_INSTALL ninja -C build install
cd -
