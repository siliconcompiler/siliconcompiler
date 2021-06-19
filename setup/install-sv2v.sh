#!/bin/sh
mkdir -p deps
cd deps

curl -sSL https://get.haskellstack.org/ | sh

git clone https://github.com/zachjs/sv2v.git
cd sv2v
make
cd -
