#!/bin/sh

set -ex

src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

if [ ! -z ${PREFIX} ]; then
    export PATH="$PREFIX/bin:$PATH"
fi

sudo yum install -y git gcc-c++ wget
sudo yum install -y tcl-tclreadline-devel \
    bison flex zlib-devel automake autoconf
sudo yum install -y \
    https://mirror.stream.centos.org/9-stream/AppStream/x86_64/os/Packages/flex-2.6.4-9.el9.x86_64.rpm \
    https://mirror.stream.centos.org/9-stream/AppStream/x86_64/os/Packages/readline-devel-8.1-4.el9.x86_64.rpm \
    https://rpmfind.net/linux/centos-stream/9-stream/AppStream/x86_64/os/Packages/tcl-devel-8.6.10-7.el9.x86_64.rpm

mkdir -p deps
cd deps

python3 -m venv .opensta --clear
. .opensta/bin/activate
python3 -m pip install cmake==3.31.6

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

if [ ! -z ${PREFIX} ]; then
    cmake_args="-DCMAKE_INSTALL_PREFIX=$PREFIX"
    config_prefix="--prefix=$PREFIX"
    export PATH="$PREFIX/bin:$PATH"
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
$SUDO_INSTALL make install

cd ../../..
# cudd
mkdir -p cudd
cd cudd
git clone --depth=1 -b 3.0.0 https://github.com/The-OpenROAD-Project/cudd.git
cd cudd
autoreconf
./configure $config_prefix
make -j$(nproc)
$SUDO_INSTALL make install

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
$SUDO_INSTALL make -j$(nproc) install

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
$SUDO_INSTALL make install

cd -
