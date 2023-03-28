#!/bin/bash

# Install dependencies
yum --disablerepo=epel -y update ca-certificates
yum install -y zlib-devel graphviz xorg-x11-server-Xvfb wget

# Install Klayout (for chip.show() test)
wget --no-check-certificate https://www.klayout.org/downloads/CentOS_7/klayout-0.28.3-0.x86_64.rpm
yum install -y python3 ruby qt-x11
# This may fail on ARM64
rpm -i klayout-0.28.3-0.x86_64.rpm || true
