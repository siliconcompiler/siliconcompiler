#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool vpr --field git-url) vpr
cd vpr
git checkout $(python3 ${src_path}/_tools.py --tool vpr --field git-commit)

./install_apt_packages.sh

args=
if [ ! -z ${PREFIX} ]; then
    args="-DCMAKE_INSTALL_PREFIX=$PREFIX"
fi

# Remove testing build
sed -i 's/enable_testing()//g' CMakeLists.txt

# Build
mkdir -p build
cd build
cmake .. $args -DCMAKE_BUILD_TYPE=release -G 'Unix Makefiles'
make -j$(nproc)
sudo make install
