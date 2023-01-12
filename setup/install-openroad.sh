#!/bin/sh
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

mkdir -p deps
cd deps

git clone https://github.com/The-OpenROAD-Project/OpenROAD.git
cd OpenROAD
git checkout a97f6efae06ba2dffa32dc01dd3ff9575264490b
git submodule update --init --recursive

sudo ./etc/DependencyInstaller.sh

./etc/Build.sh

cd build
sudo make install

cd -
