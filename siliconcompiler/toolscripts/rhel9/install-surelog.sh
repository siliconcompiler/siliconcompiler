#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

# Install prerequisites only when they are missing
. "${src_path}/_prereqs.sh"

# These dependencies are up-to-date with instructions from the INSTALL.md from the commit we are pinned to below
install_prereqs gcc-toolset-12
# The 'devel' repository is disabled by default. Enabling and disabling it is
# root-only work whose only purpose is the install between them, so the whole
# block is skipped when those packages are already present.
devel_pkgs="libuuid-devel java-11-openjdk-devel python3 zlib-static openssl-devel"
if prereqs_missing $devel_pkgs; then
    sudo dnf config-manager --set-enabled devel || true
    install_prereqs $devel_pkgs
    sudo dnf config-manager --set-disabled devel || true
fi

install_prereqs git

mkdir -p deps
cd deps

python3 -m venv .surelog --clear
. .surelog/bin/activate
python3 -m pip install cmake==3.31.6
python3 -m pip install orderedmultidict

git clone $(python3 ${src_path}/_tools.py --tool surelog --field git-url) surelog
cd surelog
git checkout $(python3 ${src_path}/_tools.py --tool surelog --field git-commit)
git submodule update --init --recursive

scl run gcc-toolset-12 "LDFLAGS=\"-lrt\" make -j${NPROC:-$(nproc)}"

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

$SUDO_INSTALL make -C build install

cd -
