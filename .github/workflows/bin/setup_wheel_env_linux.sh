#!/bin/bash

# Install dependencies
yum --disablerepo=epel update ca-certificates
yum update
yum install -y libuuid-devel zlib-devel java-1.8.0-openjdk-devel graphviz xorg-x11-server-Xvfb wget

# Install Klayout (for chip.show() test)
wget --no-check-certificate https://www.klayout.org/downloads/CentOS_7/klayout-0.27.5-0.x86_64.rpm
yum install -y python3 ruby qt-x11
rpm -i klayout-0.27.5-0.x86_64.rpm

# Build surelog (install prefix defined outside file)
git submodule update --init --recursive third_party/tools/surelog
cd third_party/tools/surelog
# Fix insecure Git protocol
sed -i 's/git:\/\/github.com\/nemtrif\/utfcpp/https:\/\/github.com\/nemtrif\/utfcpp/g' third_party/antlr4_fast/runtime/Cpp/runtime/CMakeLists.txt

export LDFLAGS="-lrt"
make
make install

cd -

# Hack because Surelog does not search lib64 install directory
mkdir -p siliconcompiler/tools/surelog/lib/surelog/sv/
cp siliconcompiler/tools/surelog/lib64/surelog/sv/builtin.sv siliconcompiler/tools/surelog/lib/surelog/sv/builtin.sv
