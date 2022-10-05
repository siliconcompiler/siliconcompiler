#!/bin/sh

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

sudo apt-get install -y build-essential cmake git pkg-config tclsh swig uuid-dev libgoogle-perftools-dev python3 python3-dev
sudo apt-get install -y default-jre

cd ${src_path}/..
git submodule update --init --recursive third_party/tools/surelog
cd third_party/tools/surelog

make
sudo make install
cd -
