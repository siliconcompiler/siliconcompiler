#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

mkdir -p deps
cd deps

sudo apt-get install -y curl git

haskell_args=""
if [ ! -z ${PREFIX} ]; then
    haskell_args="-d $PREFIX"
    export PATH="$PREFIX:$PATH"
fi

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

curl -sSL https://get.haskellstack.org/ | $SUDO_INSTALL sh -s - -f $haskell_args

git clone $(python3 ${src_path}/_tools.py --tool sv2v --field git-url) sv2v
cd sv2v
git checkout $(python3 ${src_path}/_tools.py --tool sv2v --field git-commit)

make -j$(nproc)

if [ ! -z ${PREFIX} ]; then
    $SUDO_INSTALL mkdir -p ${PREFIX}/bin/
    $SUDO_INSTALL cp bin/* ${PREFIX}/bin/
fi

cd -
