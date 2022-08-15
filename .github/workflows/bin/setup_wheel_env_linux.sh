#!/bin/bash

# Install dependencies
yum --disablerepo=epel -y update ca-certificates
yum install -y libuuid-devel zlib-devel java-11-openjdk-devel graphviz xorg-x11-server-Xvfb wget

# Install Klayout (for chip.show() test)
wget --no-check-certificate https://www.klayout.org/downloads/CentOS_7/klayout-0.27.5-0.x86_64.rpm
yum install -y python3 ruby qt-x11
rpm -i klayout-0.27.5-0.x86_64.rpm

# Required for Surelog
pip3 install orderedmultidict

# Build surelog (install prefix defined outside file)
git submodule update --init --recursive third_party/tools/surelog
cd third_party/tools/surelog

export LDFLAGS="-lrt"
make
make install

cd -
