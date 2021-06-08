#!/bin/sh
sudo apt-get install -y pkg-config build-essential libatomic-ops-dev python3 bison flex libreadline-dev gawk libffi-dev git graphviz tcl xdot libboost-system-dev libboost-python-dev libboost-filesystem-dev zlib1g-dev cmake swig libeigen3-dev
sudo apt-get install -y libboost-test-dev libspdlog-dev libqt5opengl5-dev

wget -q http://lemon.cs.elte.hu/pub/sources/lemon-1.3.1.tar.gz
tar -xf lemon-1.3.1.tar.gz
cd lemon-1.3.1
cmake -B build .
sudo cmake --build build -j $(nproc) --target install
cd -

wget -q https://prdownloads.sourceforge.net/tcl/tcl8.6.10-src.tar.gz
tar -xf tcl8.6.10-src.tar.gz
cd tcl8.6.10/unix
./configure
make
sudo make install
cd -

sudo ln -s /usr/bin/python3 /usr/bin/python
sudo ln -s /usr/local/lib/libtcl8.6.so /usr/local/lib/libtcl.so

git clone https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts
cd OpenROAD-flow-scripts
./build_openroad.sh -o
cd -

echo 'source /home/vagrant/OpenROAD-flow-scripts/setup_env.sh' >> ~/.bashrc
