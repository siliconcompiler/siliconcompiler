#!/bin/sh
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool openroad --field git-url) openroad
cd openroad
git checkout $(python3 ${src_path}/_tools.py --tool openroad --field git-commit)
git submodule update --init --recursive

sudo ./etc/DependencyInstaller.sh

./etc/Build.sh

cd build
sudo make install

cd -
