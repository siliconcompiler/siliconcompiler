#!/bin/bash
sudo yum groupinstall -y 'Development Tools'
sudo yum install -y pkgconfig bzip2 openssl-devel pth libatomic bison flex readline-devel gawk libffi-devel git graphviz zlib-devel wget
sudo yum install -y qt5-qt3d-devel

mkdir -p deps
cd deps

# If the user has not already set up a modern toolchain, install:
# cmake 3.22.1, Python 3.9.9, GNU toolchain 11.2.0
# These tools are out-of-date in the default package repos, but users may
# prefer to install newer versions by using newer package lists with yum.
# The GNU toolchain takes an especially long time to build.
if [[ ! -z "${RHEL7_OPENROAD_INSTALL_DEVTOOLS}" ]]; then
    # RHEL 7 cmake RPM is out of date.
    wget -q https://github.com/Kitware/CMake/releases/download/v3.22.1/cmake-3.22.1.tar.gz
    tar -xf cmake-3.22.1.tar.gz
    cd cmake-3.22.1
    ./bootstrap --prefix=/usr
    make
    sudo make install
    sudo ldconfig
    cd -

    wget -q http://ftp.gnu.org/gnu/gcc/gcc-11.2.0/gcc-11.2.0.tar.gz
    tar -xf gcc-11.2.0.tar.gz
    mkdir -p gcc-11.2.0/build
    cd gcc-11.2.0
    ./contrib/download_prerequisites
    cd build
    ../configure --enable-languages=all --disable-multilib
    make -j $(nproc)
    sudo make install
    export AR=/usr/local/bin/gcc-ar
    export CC=/usr/local/bin/gcc
    export CXX=/usr/local/bin/g++
    export LD_LIBRARY_PATH=/usr/local/lib64
    cd ../..

    # Build Python from source. RHEL 7 has 3.6.8, and no -devel package.
    wget -q https://www.python.org/ftp/python/3.9.9/Python-3.9.9.tgz
    tar -xf Python-3.9.9.tgz
    cd Python-3.9.9
    ./configure --prefix=/usr
    make
    sudo make install
    cd -

    # Boost C++ libraries.
    wget -q https://boostorg.jfrog.io/artifactory/main/release/1.78.0/source/boost_1_78_0.tar.gz
    tar -xf boost_1_78_0.tar.gz
    sudo cp -R boost_1_78_0/boost/ /usr/include/boost/
fi

# Install xdot; no RPM package, but it's a Python script.
sudo pip3 install xdot

# SWIG version in RHEL 7 is too old.
sudo yum remove -y swig
wget -q http://prdownloads.sourceforge.net/swig/swig-4.0.2.tar.gz
tar -xf swig-4.0.2.tar.gz
cd swig-4.0.2
./configure --prefix=/usr
make
sudo make install
cd -

# spdlog-devel not included in default yum lists.
git clone https://github.com/gabime/spdlog.git
wget -q https://github.com/gabime/spdlog/archive/refs/tags/v1.9.2.tar.gz
tar -xf v1.9.2.tar.gz
mkdir -p spdlog-1.9.2/build
cd spdlog-1.9.2/build
cmake ..
make
sudo make install
cd -

# eigen3-devel not included in default yum lists.
wget -q https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.bz2
tar -xf eigen-3.4.0.tar.bz2
mkdir -p eigen-3.4.0/build
cd eigen-3.4.0/build
cmake ..
make
sudo make install
cd -

# Build/install v1.3.1 of Lemon libs.
wget -q http://lemon.cs.elte.hu/pub/sources/lemon-1.3.1.tar.gz
tar -xf lemon-1.3.1.tar.gz
cd lemon-1.3.1
cmake -B build .
sudo cmake --build build -j $(nproc) --target install
cd -

# Ensure TCL 8.6 libs are installed in correct location.
wget -q http://prdownloads.sourceforge.net/tcl/tcl8.6.10-src.tar.gz
tar -xf tcl8.6.10-src.tar.gz
cd tcl8.6.10/unix
./configure --prefix=/usr/
make
sudo make install
sudo ln -s /usr/lib/libtcl8.6.so /usr/lib/libtcl.so
sudo ln -s /usr/bin/tclsh8.6 /usr/bin/tclsh
sudo ldconfig
cd -


cd ..

# Install OpenROAD tools.
cd ..
git submodule update --init --recursive third_party/tools/openroad
cd third_party/tools/openroad
./build_openroad.sh -o

# Ensure that the correct C library is used if we needed to build GCC.
if [[ ! -z "${RHEL7_OPENROAD_INSTALL_DEVTOOLS}" ]]; then
    echo "export LD_LIBRARY_PATH=/usr/local/lib64" >> $(pwd)/setup_env.sh
fi

echo "Done!"
echo ""
echo "Please run \"source $(pwd)/setup_env.sh\", and add that line to your ~/.bashrc file"

cd -
