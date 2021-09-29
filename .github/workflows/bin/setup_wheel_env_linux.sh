#!/bin/bash

# Install dependencies
yum install -y libuuid-devel zlib-devel java-1.8.0-openjdk-devel

# Build surelog (install prefix defined outside file)
cd third_party/tools/surelog

export LDFLAGS="-lrt"
make
make install
