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

install_prereqs git curl wget

mkdir -p deps
cd deps

if [ "$(uname -m)" = "x86_64" ]; then
    install_prereqs ghc libghc-regex-compat-dev libghc-syb-dev \
        libghc-old-time-dev libghc-split-dev

    # bsc 2026.01 swapped its vendored strict MVar for Hackage's
    # strict-concurrency, and src/Makefile gates the build on
    # "ghc-pkg list strict-concurrency". Nothing packages it: there is
    # no libghc-strict-concurrency-dev, and Ubuntu 24.04's cabal 3.8 can
    # no longer reach Hackage at all, its built-in root keys having
    # stopped verifying. So build it from a pinned release, with the
    # Cabal library that ghc already bundles.
    #
    # --user keeps it in $HOME: it is a dependency of the Haskell
    # compile only, and has no place in an install prefix, which is
    # often shared and which is what ships in the container image.
    hs_pkg=strict-concurrency-0.2.4.3
    hs_url=https://hackage.haskell.org/package/${hs_pkg}
    # Hackage revises .cabal files in place to widen version bounds after a
    # release, and the tarball keeps the original: 0.2.4.3 as shipped caps
    # deepseq below 1.5, which is the version Ubuntu 26.04's ghc provides,
    # and revision 1 is what lifts the cap to 1.6.
    #
    # Take that revision by number and check what arrives. A numbered
    # revision is immutable, where the unnumbered .cabal always serves
    # whatever the newest revision has become, so pinning the version alone
    # would have left the bounds this builds against free to move.
    hs_cabal_rev=1
    hs_cabal_sha256=fede3d515b877b56623ac1ccacbf17c326baded87640af0f10c27c66dd742f49
    hs_tar_sha256=02d934ec5053d3d42031798e5a3cd25547ccde5973d562f9fc943d635d9956c0
    if [ -z "$(ghc-pkg list --simple-output strict-concurrency)" ]; then
        # Both downloads land in a file and are checked before anything reads
        # them. Piping the archive straight into tar would unpack whatever
        # arrived, and a short read would leave a half-extracted tree behind.
        wget -q -O ${hs_pkg}.tar.gz ${hs_url}/${hs_pkg}.tar.gz
        echo "${hs_tar_sha256}  ${hs_pkg}.tar.gz" | sha256sum --quiet -c -
        tar xzf ${hs_pkg}.tar.gz
        cd ${hs_pkg}
        wget -q -O strict-concurrency.cabal ${hs_url}/revision/${hs_cabal_rev}.cabal
        echo "${hs_cabal_sha256}  strict-concurrency.cabal" | sha256sum --quiet -c -
        # Build-type: Simple, so the stock Setup is the whole build system.
        printf 'import Distribution.Simple\nmain = defaultMain\n' > Setup.hs
        runghc Setup.hs configure --user
        runghc Setup.hs build
        runghc Setup.hs install
        cd -
    fi
else
    install_prereqs build-essential curl libffi-dev libffi8 libgmp-dev \
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
fi

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

