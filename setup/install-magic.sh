#!/bin/sh

sudo apt-get install -y build-essential m4 tcsh csh libx11-dev tcl-dev tk-dev

mkdir -p deps
cd deps

git clone https://github.com/RTimothyEdwards/magic.git
cd magic

./configure
make
sudo make install
