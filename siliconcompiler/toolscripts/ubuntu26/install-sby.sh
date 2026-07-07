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

# sby is pure python; it drives yosys / yosys-smtbmc (installed separately) and
# needs click at runtime. The remaining packages build the bitwuzla SMT solver
# used by the default sby engine (see below).
sudo apt-get install -y git python3 python3-click python3-venv python3-pip \
                        build-essential cmake pkg-config ninja-build \
                        libgmp-dev libmpfr-dev

mkdir -p deps
cd deps

# --- SymbiYosys (sby) ---
git clone $(python3 ${src_path}/_tools.py --tool sby --field git-url) sby
cd sby
git checkout $(python3 ${src_path}/_tools.py --tool sby --field git-commit)
$SUDO_INSTALL make install PREFIX="$PREFIX"
cd -

# --- Bitwuzla (SMT solver for the default 'smtbmc bitwuzla' engine) ---
# Built here, not as its own tool: the CI image build does not support chaining
# docker-depends (sby already depends on yosys). meson is installed in a venv
# because distro packages can be older than bitwuzla requires.
python3 -m venv .bitwuzla --clear
. .bitwuzla/bin/activate
python3 -m pip install meson

# preserve PATH under sudo so the venv's meson is visible during 'ninja install'
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
fi

git clone $(python3 ${src_path}/_tools.py --tool bitwuzla --field git-url) bitwuzla
cd bitwuzla
git checkout $(python3 ${src_path}/_tools.py --tool bitwuzla --field git-commit)

args=
if [ ! -z ${PREFIX} ]; then
    args="--prefix $PREFIX"
fi
./configure.py $args
ninja -C build
$SUDO_INSTALL ninja -C build install
cd -

deactivate
