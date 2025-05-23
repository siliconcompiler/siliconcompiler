#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

sudo apt-get install -y tcl-dev build-essential pkg-config \
    autoconf gperf flex bison

sudo apt-get install -y git curl

mkdir -p deps
cd deps

if [ "$(uname -m)" = "x86_64" ]; then
    sudo apt-get install -y ghc libghc-regex-compat-dev libghc-syb-dev \
        libghc-old-time-dev libghc-split-dev
else
    sudo apt-get install -y build-essential curl libffi-dev libffi8 libgmp-dev \
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

    cabal v1-install regex-compat syb old-time split
fi

git clone $(python3 ${src_path}/_tools.py --tool bluespec --field git-url) bluespec
cd bluespec
git checkout $(python3 ${src_path}/_tools.py --tool bluespec --field git-commit)
git submodule update --init --recursive

make -j$(nproc) install-src

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

