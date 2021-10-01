#!/bin/bash

# Install Surelog
cd third_party/tools/surelog
make
make install PREFIX=$GITHUB_WORKSPACE/siliconcompiler/tools/surelog
