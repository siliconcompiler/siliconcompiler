#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo apt-get install -y build-essential gperf libgtk-3-dev \
    libbz2-dev libjudy-dev liblzma-dev tcl-dev tk-dev autotools-dev \
    automake

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool gtkwave --field git-url) gtkwave
cd gtkwave
git checkout $(python3 ${src_path}/_tools.py --tool gtkwave --field git-commit)

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

cd gtkwave3-gtk3

./autogen.sh
./configure --enable-gtk3 $args
make -j$(nproc)
sudo make install
