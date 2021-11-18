#!/bin/sh
sudo apt-get install -y git perl python3 make autoconf g++ flex bison ccache
sudo apt-get install -y libgoogle-perftools-dev numactl perl-doc
sudo apt-get install -y libfl2
sudo apt-get install -y libfl-dev
sudo apt-get install -y zlibc zlib1g zlib1g-dev

mkdir -p deps
cd deps

git clone https://github.com/verilator/verilator

unset VERILATOR_ROOT
cd verilator

git checkout v4.028

autoconf
./configure
make -j$(nproc)
sudo make install

cd -
