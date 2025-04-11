#!/bin/sh

set -e

src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo apt-get install -y git build-essential wget
sudo apt-get install -y tcl-dev tcl-tclreadline \
    bison flex libfl-dev zlib1g-dev automake autotools-dev

mkdir -p deps
cd deps

python3 -m venv .opensta --clear
. .opensta/bin/activate
python3 -m pip install cmake==3.31.6

if [ ! -z ${PREFIX} ]; then
    cmake_args="-DCMAKE_INSTALL_PREFIX=$PREFIX"
    config_prefix="--prefix=$PREFIX"
fi

# eigen
mkdir -p eigen3
cd eigen3
git clone --depth=1 -b 3.4 https://gitlab.com/libeigen/eigen.git
cd eigen
mkdir build
cd build
cmake $cmake_args ..
make -j$(nproc)
sudo make install

cd ../../..
# cudd
mkdir -p cudd
cd cudd
git clone --depth=1 -b 3.0.0 https://github.com/The-OpenROAD-Project/cudd.git
cd cudd
autoreconf
./configure $config_prefix
make -j$(nproc)
sudo make install

cd ../..
#swig
wget -O swig.tar.gz https://github.com/swig/swig/archive/v4.1.0.tar.gz
tar xfz swig.tar.gz
cd swig-4.1.0

wget https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.42/pcre2-10.42.tar.gz
./Tools/pcre-build.sh

./autogen.sh
./configure $config_prefix
make -j$(nproc)
sudo make -j$(nproc) install

cd ../..
# opensta
git clone $(python3 ${src_path}/_tools.py --tool opensta --field git-url) opensta
cd opensta
git checkout $(python3 ${src_path}/_tools.py --tool opensta --field git-commit)
git submodule update --init --recursive

mkdir -p build
cd build
cmake .. $cmake_args
make -j$(nproc)
sudo make install

cd -
