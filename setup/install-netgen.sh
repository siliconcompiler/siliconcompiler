#!/bin/sh

sudo apt-get install -y build-essential tcl-dev tk-dev

mkdir -p deps
cd deps

git clone https://github.com/RTimothyEdwards/netgen.git
cd netgen

git checkout 1.5.210

./configure
make
sudo make install
