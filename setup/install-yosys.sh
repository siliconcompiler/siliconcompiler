#!/bin/sh

# From: https://github.com/YosysHQ/yosys/blob/f2c689403ace0637b7455bac8f1e8d4bc312e74f/README.md
sudo apt-get install build-essential clang bison flex \
	libreadline-dev gawk tcl-dev libffi-dev git \
	graphviz xdot pkg-config python3 libboost-system-dev \
	libboost-python-dev libboost-filesystem-dev zlib1g-dev

mkdir -p deps/yosys
cd deps/yosys

wget https://github.com/YosysHQ/yosys/archive/refs/tags/yosys-0.24.tar.gz
tar xvf yosys-0.24.tar.gz --strip-components=1

make -j
sudo make install
cd -
