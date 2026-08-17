#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

# Install prerequisites only when they are missing
. "${src_path}/_prereqs.sh"

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

install_prereqs wget lsb-core

mkdir -p deps
cd deps

pkg_version=$(python3 ${src_path}/_tools.py --tool klayout --field version)
version=$(lsb_release -sr)
arch=$(dpkg --print-architecture)

# KLayout only publishes amd64 .debs for Ubuntu; on other architectures
# (e.g. arm64) fall back to the distro package from the universe repository.
if [ "$arch" != "amd64" ]; then
    # KLayout itself, not a prerequisite, so this install is unconditional and
    # needs the package index refreshed if install_prereqs did not do it.
    apt_update
    sudo apt-get install -y klayout
    cd -
    exit 0
fi

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
# Install package. apt resolves the .deb's dependencies from the package index,
# so refresh it if install_prereqs above had nothing to install.
apt_update
sudo apt-get install -y ./klayout.deb

if [ ! -z ${SC_PREFIX+x} ]; then
    sudo cp ./klayout.deb "${SC_PREFIX}/"
fi

cd -
