#!/bin/sh

set -e

src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

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
sudo ./etc/DependencyInstaller.sh $deps_args

cmake_args="-DENABLE_TESTS=OFF"
if [ ! -z ${PREFIX} ]; then
    cmake_args="$cmake_args -DCMAKE_INSTALL_PREFIX=$PREFIX"
fi

./etc/Build.sh -cmake="$cmake_args"

cd build
sudo make install

cd -
