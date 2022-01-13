#!/bin/sh

# Install dependencies required to build SC from source on a fresh RHEL 8.x or
# 7.x install.

sudo yum groupinstall -y "Development Tools"
sudo yum install -y zlib-devel

if grep -q -i "release 7" /etc/redhat-release
then
  sudo subscription-manager repos --enable rhel-server-rhscl-7-rpms
  sudo yum -y install rh-python36
  echo "To activate Python, run 'scl enable rh-python36 bash' (and consider adding this to your ~/.bashrc)"
else
  sudo yum -y install python3-devel
fi
