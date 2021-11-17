#!/bin/sh

sudo apt-get install -y build-essential tcl-dev tk-dev

mkdir -p deps
cd deps

git clone https://github.com/RTimothyEdwards/netgen.git
cd netgen

# TODO: our tests don't pass with newer versions
git checkout 1.5.192

./configure
make
sudo make install
