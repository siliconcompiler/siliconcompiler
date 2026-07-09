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

sudo apt-get install -y git build-essential cmake libgmp-dev curl \
                        python3 python3-pip

mkdir -p deps
cd deps

# boolector bundles lingeling (2018-era C) and declares cmake_minimum_required
# floors that current toolchains reject: gcc >= 14 turns several legacy warnings
# (implicit-function-declaration, implicit-int, incompatible-pointer-types,
# int-conversion) into hard errors, and cmake >= 4 drops pre-3.5 compatibility.
# Wrap gcc/cc to keep those diagnostics as warnings, and restore the old cmake
# policy floor, so the solver still builds. Both are no-ops on older toolchains.
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
