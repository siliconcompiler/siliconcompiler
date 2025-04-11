#!/bin/bash

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

# From: https://github.com/YosysHQ/yosys/blob/f2c689403ace0637b7455bac8f1e8d4bc312e74f/README.md
sudo yum group install -y "Development Tools"
sudo yum install -y bison flex readline-devel gawk \
	tcl-devel libffi-devel zlib-devel boost-devel

sudo yum install -y git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool yosys --field git-url) yosys
cd yosys
git checkout $(python3 ${src_path}/_tools.py --tool yosys --field git-commit)
git submodule update --init --recursive

make -j$(nproc) PREFIX="$PREFIX"
sudo make install PREFIX="$PREFIX"
cd -
