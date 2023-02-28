#!/bin/bash

# Get directory of setup scripts
src_path=$(cd -- "$(dirname "$0")/../../../" >/dev/null 2>&1 ; pwd -P)

# Install dependencies
pip3 install orderedmultidict

# Install Surelog
git clone $(python3 ${src_path}/setup/_tools.py --tool surelog --field git-url) surelog
cd surelog
git checkout $(python3 ${src_path}/setup/_tools.py --tool surelog --field git-commit)
git submodule update --init --recursive

export ADDITIONAL_CMAKE_OPTIONS=-DPython3_ROOT_DIR=${pythonLocation}
make
make install PREFIX=$GITHUB_WORKSPACE/siliconcompiler/tools/surelog
