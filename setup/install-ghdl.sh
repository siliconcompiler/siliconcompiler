#!/bin/sh

sudo apt-get install -y gnat libgnat-7

mkdir -p deps
cd deps
git clone https://github.com/ghdl/ghdl.git
cd ghdl

./configure
make
sudo make install
cd -
