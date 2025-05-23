#!/bin/sh

set -ex

src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

if [ ! -z ${PREFIX} ]; then
    export PATH="$PREFIX/bin:$PATH"
fi

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

sudo apt-get install -y git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool openroad --field git-url) openroad
cd openroad
git checkout $(python3 ${src_path}/_tools.py --tool openroad --field git-commit)
git submodule update --init --recursive

deps_args=""
if [ ! -z ${PREFIX} ]; then
    deps_args="-prefix=$PREFIX"
fi
sudo ./etc/DependencyInstaller.sh -base
sudo rm -f etc/openroad_deps_prefixes.txt
$SUDO_INSTALL ./etc/DependencyInstaller.sh -common $deps_args

cmake_args="-DENABLE_TESTS=OFF"
if [ ! -z ${PREFIX} ]; then
    cmake_args="$cmake_args -DCMAKE_INSTALL_PREFIX=$PREFIX"
fi

./etc/Build.sh -cmake="$cmake_args"

cd build
$SUDO_INSTALL make install

cd -
