#!/bin/sh

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

sudo apt-get install -y build-essential cmake git pkg-config tclsh swig uuid-dev libgoogle-perftools-dev python3 python3-dev
sudo apt-get install -y default-jre

mkdir -p deps
cd deps

git clone https://github.com/chipsalliance/Surelog.git
cd Surelog
git checkout ad83eedc7de32ec15a3f7b4e271c6b45ddf547eb

make
sudo make install

cd -
