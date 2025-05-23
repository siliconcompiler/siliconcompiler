#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

sudo yum install -y wget

mkdir -p deps
cd deps

klayout_version=$(python3 ${src_path}/_tools.py --tool klayout --field version)
wget --no-check-certificate \
    -O klayout.rpm \
    "https://www.klayout.org/downloads/CentOS_8/klayout-${klayout_version}-0.x86_64.rpm"
sudo yum install -y ./klayout.rpm

cd -
