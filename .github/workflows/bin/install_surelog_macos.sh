#!/bin/bash

# Install dependencies
pip3 install orderedmultidict

# Install Surelog
git clone https://github.com/chipsalliance/Surelog.git $GITHUB_WORKSPACE/surelog
cd $GITHUB_WORKSPACE/surelog
git checkout ad83eedc7de32ec15a3f7b4e271c6b45ddf547eb
git submodule update --init --recursive

export ADDITIONAL_CMAKE_OPTIONS=-DPython3_ROOT_DIR=${pythonLocation}
make
make install PREFIX=$GITHUB_WORKSPACE/siliconcompiler/tools/surelog
