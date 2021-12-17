#!/bin/sh

sudo apt-get install -y autoconf autoconf-archive automake libtool g++ gcc-4.8 \
    g++-4.8 gcc-5 g++-5 gcc-6 g++-6 gcc-7 g++-7 gcc-8 g++-8 gcc-4.8-plugin-dev \
    gcc-5-plugin-dev gcc-6-plugin-dev gcc-7-plugin-dev  gcc-8-plugin-dev \
    gcc-4.8-multilib gcc-5-multilib gcc-6-multilib gcc-7-multilib gcc-8-multilib \
    g++-4.8-multilib g++-5-multilib g++-6-multilib g++-7-multilib g++-8-multilib \
    gfortran-4.8 gfortran-4.8-multilib gfortran-5 gfortran-5-multilib gfortran-6 \
    gfortran-6-multilib gfortran-7 gfortran-7-multilib gfortran-8 \
    gfortran-8-multilib clang-4.0 libclang-4.0-dev libclang-6.0-dev clang-6.0 \
    libclang-6.0-dev clang-7 libclang-7-dev libbdd-dev libboost-all-dev \
    libmpc-dev libmpfr-dev libxml2-dev liblzma-dev libmpfi-dev zlib1g-dev \
    libicu-dev bison doxygen flex graphviz iverilog verilator make \
    libsuitesparse-dev libglpk-dev

mkdir -p deps
cd deps
git clone https://github.com/ferrandi/PandA-bambu.git
cd PandA-bambu

make -f Makefile.init

mkdir obj
cd obj

../configure --enable-flopoco --enable-release --prefix=/opt/panda
make
sudo make install

cd ../../../
