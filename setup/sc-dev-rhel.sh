#!/bin/sh

# Install dependencies required to build SC from source on a fresh RHEL 8.x
# install.

sudo yum groupinstall -y "Development Tools"
sudo yum install -y zlib-devel python3-devel
