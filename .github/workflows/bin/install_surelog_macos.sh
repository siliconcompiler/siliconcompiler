#!/bin/bash

# Install dependencies
pip3 install orderedmultidict

# Install Surelog
git clone $(python3 $GITHUB_WORKSPACE/setup/_tools.py --tool surelog --field git-url) $GITHUB_WORKSPACE/surelog
cd $GITHUB_WORKSPACE/surelog
git checkout $(python3 $GITHUB_WORKSPACE/setup/_tools.py --tool surelog --field git-commit)
git submodule update --init --recursive

export ADDITIONAL_CMAKE_OPTIONS=-DPython3_ROOT_DIR=${pythonLocation}
make
make install PREFIX=$GITHUB_WORKSPACE/siliconcompiler/tools/surelog
