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
# build the two selectable SMT solvers -- bitwuzla (default) and boolector -- and
# bitwuzla's GMP/MPFR deps. boolector links the apt libgmp.
sudo apt-get install -y git python3 python3-pip build-essential cmake curl \
                        ninja-build pkg-config xz-utils m4 file libgmp-dev python3-venv

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

# boolector bundles lingeling (2018-era C) and declares cmake_minimum_required
# floors that current toolchains reject: gcc >= 14 turns several legacy warnings
# (implicit-function-declaration, implicit-int, incompatible-pointer-types,
# int-conversion) into hard errors, and cmake >= 4 drops pre-3.5 compatibility.
# Ubuntu 26 ships both (gcc 15, cmake 4). Wrap gcc/cc to keep those diagnostics as
# warnings and restore the old cmake policy floor so boolector still builds. Both
# are no-ops on the older toolchains in Ubuntu 22/24, and on bitwuzla below.
compat_flags="-Wno-error=implicit-function-declaration -Wno-error=implicit-int"
compat_flags="$compat_flags -Wno-error=incompatible-pointer-types -Wno-error=int-conversion"
mkdir -p ccshim
for cc in gcc cc; do
    ccpath=$(command -v "$cc") || continue
    printf '#!/bin/sh\nexec "%s" "$@" %s\n' "$ccpath" "$compat_flags" > "ccshim/$cc"
    chmod +x "ccshim/$cc"
done
export PATH="$PWD/ccshim:$PATH"
export CMAKE_POLICY_VERSION_MINIMUM=3.5

# --- Boolector (selectable via the 'smtbmc boolector' engine) ---
# Built here, not as its own tool, because the CI image build does not support
# chaining docker-depends (sby already depends on yosys). Links the apt libgmp,
# which is ABI-compatible at runtime with the newer GMP built below for bitwuzla.
git clone $(python3 ${src_path}/_tools.py --tool boolector --field git-url) boolector
cd boolector
git checkout $(python3 ${src_path}/_tools.py --tool boolector --field git-commit)
./contrib/setup-lingeling.sh
./contrib/setup-btor2tools.sh
args=
if [ ! -z ${PREFIX} ]; then
    args="--prefix $PREFIX"
fi
./configure.sh $args
make -C build -j"${NPROC:-$(nproc)}"
$SUDO_INSTALL make -C build install
cd -

# bitwuzla needs GMP >= 6.3 and MPFR >= 4.2.1, newer than Ubuntu 22 ships, and
# both must live in $PREFIX so they travel with the tool image (only $PREFIX is
# copied, like click above). Build them from source into $PREFIX on every release
# for a uniform, self-contained result. '-std=gnu17' keeps GMP's configure probes
# valid under the C23 default of gcc >= 15. Both install their own pkg-config
# files (gmp.pc/mpfr.pc), which bitwuzla's meson discovers via PKG_CONFIG_PATH.
prefix="${PREFIX:-/usr/local}"

curl -fL https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz -o gmp.tar.xz
tar xf gmp.tar.xz
cd gmp-6.3.0
./configure CC="gcc -std=gnu17" CXX="g++ -std=gnu++17" \
    --prefix="$prefix" --enable-static --enable-shared --enable-cxx
make -j"${NPROC:-$(nproc)}"
$SUDO_INSTALL make install
cd -

curl -fL https://ftp.gnu.org/gnu/mpfr/mpfr-4.2.2.tar.xz -o mpfr.tar.xz
tar xf mpfr.tar.xz
cd mpfr-4.2.2
./configure CC="gcc -std=gnu17" --prefix="$prefix" --with-gmp="$prefix" \
    --enable-static --enable-shared
make -j"${NPROC:-$(nproc)}"
$SUDO_INSTALL make install
cd -

export PKG_CONFIG_PATH="$prefix/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export LD_LIBRARY_PATH="$prefix/lib:${LD_LIBRARY_PATH:-}"

# meson (pinned) drives the bitwuzla build; install it in a throwaway venv so the
# system python is left untouched. Preserve the venv on PATH under sudo (as the
# other tool scripts do) so 'ninja install' -- which reinvokes meson -- finds it.
python3 -m venv .mesonvenv --clear
. .mesonvenv/bin/activate
python3 -m pip install "meson==1.8.0"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
fi

# --- Bitwuzla (the default 'smtbmc bitwuzla' engine) ---
# yosys >= 0.67 drives bitwuzla via its native '--lang' interface. Modern C++/meson
# build (it does not need the compiler shim above); CaDiCaL + SymFPU are fetched by
# meson. Shared linking uses the GMP/MPFR shared libs above (a fully static binary
# would also need static libc/libstdc++, which the base image does not ship).
git clone $(python3 ${src_path}/_tools.py --tool bitwuzla --field git-url) bitwuzla
cd bitwuzla
git checkout $(python3 ${src_path}/_tools.py --tool bitwuzla --field git-commit)
meson setup build ${PREFIX:+--prefix "$PREFIX"} --buildtype=release -Ddefault_library=shared
ninja -C build -j"${NPROC:-$(nproc)}"
$SUDO_INSTALL ninja -C build install
cd -
