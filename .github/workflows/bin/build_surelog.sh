#!/bin/bash

yum install -y libuuid-devel zlib-devel java-1.8.0-openjdk-devel

cd third_party/tools/surelog

export LDFLAGS="-lrt"

make
make install
