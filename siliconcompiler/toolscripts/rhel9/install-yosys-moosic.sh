#!/bin/bash

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool yosys-moosic --field git-url) yosys-moosic
cd yosys-moosic
git checkout $(python3 ${src_path}/_tools.py --tool yosys-moosic --field git-commit)

make -j$(nproc)
sudo PATH="$PATH" make install
cd -
