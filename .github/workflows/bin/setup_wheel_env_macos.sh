#!/bin/bash

# Install Surelog
git submodule update --init --recursive third_party/tools/surelog
cd third_party/tools/surelog
make
make install PREFIX=$GITHUB_WORKSPACE/siliconcompiler/tools/surelog
