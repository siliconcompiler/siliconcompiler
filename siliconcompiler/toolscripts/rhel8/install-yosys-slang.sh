#!/bin/bash

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

mkdir -p deps
cd deps

python3 -m venv .yosys-slang --clear
. .yosys-slang/bin/activate
python3 -m pip install cmake

git clone $(python3 ${src_path}/_tools.py --tool yosys-slang --field git-url) yosys-slang
cd yosys-slang
git checkout $(python3 ${src_path}/_tools.py --tool yosys-slang --field git-commit)
git submodule update --init --recursive

make -j$(nproc)
sudo PATH="$PATH" make install
cd -
