#!/bin/bash

# Install dependencies
yum install -y libuuid-devel zlib-devel java-1.8.0-openjdk-devel graphviz

# Build surelog (install prefix defined outside file)
cd third_party/tools/surelog

export LDFLAGS="-lrt"
make
make install

cd -

# Hack because Surelog does not search lib64 install directory
mkdir -p siliconcompiler/tools/surelog/lib/surelog/sv/
cp siliconcompiler/tools/surelog/lib64/surelog/sv/builtin.sv siliconcompiler/tools/surelog/lib/surelog/sv/builtin.sv
