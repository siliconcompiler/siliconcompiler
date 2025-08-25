#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo yum install -y wget unzip

mkdir -p deps
cd deps

version=$(python3 ${src_path}/_tools.py --tool xdm --field version)

wget -O xdm.zip https://xyce.sandia.gov/files/xyce/Binaries/xdm-${version}-Linux.zip

unzip xdm.zip

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo"
else
    SUDO_INSTALL=""
fi

$SUDO_INSTALL cp xdm*/bin/xdm_bdl $PREFIX/bin

cd -
