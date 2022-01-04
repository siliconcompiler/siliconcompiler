#!/bin/bash

# Install dependencies
yum install -y libuuid-devel zlib-devel java-1.8.0-openjdk-devel graphviz xorg-x11-server-Xvfb

# Install Klayout (for chip.show() test)
wget https://www.klayout.org/downloads/CentOS_7/klayout-0.27.5-0.x86_64.rpm
sudo rpm -i klayout-0.27.5-0.x86_64.rpm

# Build surelog (install prefix defined outside file)
git submodule update --init --recursive third_party/tools/surelog
cd third_party/tools/surelog

export LDFLAGS="-lrt"
make
make install

cd -

# Hack because Surelog does not search lib64 install directory
mkdir -p siliconcompiler/tools/surelog/lib/surelog/sv/
cp siliconcompiler/tools/surelog/lib64/surelog/sv/builtin.sv siliconcompiler/tools/surelog/lib/surelog/sv/builtin.sv
