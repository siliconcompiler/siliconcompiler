#!/bin/sh

set -e

sudo apt-get install -y cmake pkg-config bison flex libssl-dev libreadline-dev

mkdir -p deps
cd deps

git clone https://github.com/LNIS-Projects/OpenFPGA.git
cd OpenFPGA
git submodule update --init --recursive

./vtr-verilog-to-routing/install_apt_packages.sh

make \
    CMAKE_FLAGS="-DOPENFPGA_WITH_YOSYS=OFF -DOPENFPGA_WITH_YOSYS_PLUGIN=OFF -DOPENFPGA_WITH_TEST=OFF -DWITH_ABC=OFF -DWITH_YOSYS=OFF -DWITH_PARMYS=OFF -DODIN_YOSYS=OFF -DYOSYS_SV_UHDM_PLUGIN=OFF -DYOSYS_F4PGA_PLUGINS=OFF -DOPENFPGA_WITH_SWIG=OFF" \
    all -j$(nproc)
cd -
