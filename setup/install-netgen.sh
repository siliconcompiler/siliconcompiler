#!/bin/sh

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

sudo apt-get install -y build-essential tcl-dev tk-dev

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool netgen --field git-url) netgen
cd netgen
git checkout $(python3 ${src_path}/_tools.py --tool netgen --field git-commit)

./configure
make
sudo make install
