#!/bin/bash

# Install dependencies
pip3 install orderedmultidict

# Install Surelog
git submodule update --init --recursive third_party/tools/surelog
cd third_party/tools/surelog
export ADDITIONAL_CMAKE_OPTIONS=-DPython3_ROOT_DIR=${pythonLocation}
make
make install PREFIX=$GITHUB_WORKSPACE/siliconcompiler/tools/surelog
