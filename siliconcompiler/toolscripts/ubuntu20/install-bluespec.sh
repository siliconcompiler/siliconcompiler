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

install_prereqs tcl-dev build-essential pkg-config \
    autoconf gperf flex bison

install_prereqs git curl

mkdir -p deps
cd deps

# Ubuntu's ghc is too old to build bsc. It bundles bytestring 0.10, and
# BinData.hs calls Data.ByteString.indexMaybe, which arrived in bytestring
# 0.11; bytestring is a GHC boot library, so its version is the compiler's and
# cannot be raised from Hackage. Upstream INSTALL.md recommends installing GHC
# through ghcup for exactly this reason, and calls every version older than the
# 9.6.7 it tests untested.
#
# ghcup also brings its own strict-concurrency, so the pinned Hackage build
# that the distro-ghc path needed is gone with it.
install_prereqs build-essential curl libffi7 libffi-dev libgmp-dev \
    libgmp10 libncurses-dev libncurses5 libtinfo5 pkg-config
if [ ! -z ${PREFIX} ]; then
    export PATH="$PREFIX/bin:$PATH"
    export GHCUP_INSTALL_BASE_PREFIX=$PREFIX
fi

export BOOTSTRAP_HASKELL_NONINTERACTIVE=yes

curl -sSL https://get-ghcup.haskell.org | sh -s

if [ ! -z ${PREFIX} ]; then
    . ${PREFIX}/.ghcup/env
else
    . ${HOME}/.ghcup/env
fi

cabal v1-install regex-compat syb old-time split strict-concurrency

git clone $(python3 ${src_path}/_tools.py --tool bluespec --field git-url) bluespec
cd bluespec
git checkout $(python3 ${src_path}/_tools.py --tool bluespec --field git-commit)
git submodule update --init --recursive

make -j${NPROC:-$(nproc)} install-src

if [ -z ${PREFIX} ]; then
    # install
    $SUDO_INSTALL mkdir -p /opt/tools/bsc
    $SUDO_INSTALL chown $USER:$USER /opt/tools/bsc

    BSC_VERSION=$(echo 'puts [lindex [Bluetcl::version] 0]' | inst/bin/bluetcl)
    mv inst /opt/tools/bsc/bsc-${BSC_VERSION}
    ln -s /opt/tools/bsc/bsc-${BSC_VERSION} /opt/tools/bsc/latest

    echo "Please add \"export PATH=/opt/tools/bsc/latest/bin:\$PATH to your .bashrc"
fi

cd -

