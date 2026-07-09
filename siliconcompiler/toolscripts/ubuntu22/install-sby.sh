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
# 'click' dependency is bundled into the tool prefix below. The remaining
# packages build the boolector SMT solver used by the default sby engine.
sudo apt-get install -y git python3 python3-pip \
                        build-essential cmake libgmp-dev curl

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
# Ubuntu 26 ships both (gcc 15, cmake 4). Wrap gcc/cc to keep those diagnostics
# as warnings, and restore the old cmake policy floor, so the solver still
# builds. Both are no-ops on the older toolchains in Ubuntu 22/24.
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

# --- Boolector (the SMT solver the default 'smtbmc boolector' engine uses) ---
# Built here, not as its own tool, because the CI image build does not support
# chaining docker-depends (sby already depends on yosys).
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
