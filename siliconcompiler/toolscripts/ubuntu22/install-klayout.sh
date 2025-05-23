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

sudo apt-get install -y wget lsb-core

mkdir -p deps
cd deps

pkg_version=$(python3 ${src_path}/_tools.py --tool klayout --field version)
version=$(lsb_release -sr)

if [ "$version" = "18.04" ]; then
    url="https://www.klayout.org/downloads/Ubuntu-18/klayout_${pkg_version}-1_amd64.deb"
elif [ "$version" = "20.04" ]; then
    url="https://www.klayout.org/downloads/Ubuntu-20/klayout_${pkg_version}-1_amd64.deb"
elif [ "$version" = "22.04" ]; then
    url="https://www.klayout.org/downloads/Ubuntu-22/klayout_${pkg_version}-1_amd64.deb"
else
    echo "Script doesn't support Ubuntu version $version."
fi

# Fetch package
wget -O klayout.deb $url
# Install package
sudo apt-get install -y ./klayout.deb

cd -
