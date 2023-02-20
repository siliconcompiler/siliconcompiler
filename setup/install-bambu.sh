#!/bin/sh

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

sudo apt-get install -y autoconf autoconf-archive automake libtool g++ \
    gcc-7 g++-7 gcc-8 g++-8 gcc-7-plugin-dev  gcc-8-plugin-dev gcc-7-multilib \
    gcc-8-multilib g++-7-multilib g++-8-multilib gfortran-7 gfortran-7-multilib \
    gfortran-8 gfortran-8-multilib libclang-6.0-dev clang-6.0 libclang-6.0-dev \
    clang-7 libclang-7-dev libbdd-dev libboost-all-dev libmpc-dev libmpfr-dev \
    libxml2-dev liblzma-dev libmpfi-dev zlib1g-dev libicu-dev bison doxygen flex \
    graphviz iverilog verilator make libsuitesparse-dev libglpk-dev libgmp-dev

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool bambu --field git-url) bambu
cd bambu
git checkout $(python3 ${src_path}/_tools.py --tool bambu --field git-commit)

sudo mkdir -p /opt/panda
sudo chown $USER:$USER /opt/panda

make -f Makefile.init

mkdir obj
cd obj

../configure --enable-release --prefix=/opt/panda
make
make install

cd -

echo "Please add \"export PATH="/opt/panda/bin:\$PATH"\" to your .bashrc"
