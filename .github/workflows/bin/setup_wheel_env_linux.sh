#!/bin/bash

# Install dependencies
yum --disablerepo=epel -y update ca-certificates
yum install -y zlib-devel graphviz xorg-x11-server-Xvfb wget

# Install Klayout (for chip.show() test)
klayout_version=$(python3 ${src_path}/setup/_tools.py --tool klayout --field version)
wget --no-check-certificate \
    -O klayout.rpm \
    "https://www.klayout.org/downloads/CentOS_7/klayout-${klayout_version}-0.x86_64.rpm"
yum install -y python3 ruby qt-x11
# This may fail on ARM64
rpm -i klayout.rpm || true
