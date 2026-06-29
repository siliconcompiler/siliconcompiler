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

sudo apt-get update

sudo apt-get install -y wget software-properties-common

mkdir -p deps
cd deps

pkg_version=$(python3 ${src_path}/_tools.py --tool klayout --field version)
version=$(lsb_release -sr)

# KLayout does not publish a versioned Ubuntu-26 .deb, and the Ubuntu-24 build is
# not installable on 26.04 (it pins Qt5/libgit2-1.7/libruby3.2/libpython3.12).
# Use the distro package from the 26.04 universe repository instead.
if [ "$version" = "26.04" ]; then
    sudo add-apt-repository -y universe
    sudo apt-get update
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
elif [ "$version" = "24.04" ]; then
    url="https://www.klayout.org/downloads/Ubuntu-24/klayout_${pkg_version}-1_amd64.deb"
else
    echo "Script doesn't support Ubuntu version $version."
fi

# Fetch package
wget -O klayout.deb $url
# Install package
sudo apt-get install -y ./klayout.deb

if [ ! -z ${SC_PREFIX+x} ]; then
    sudo cp ./klayout.deb "${SC_PREFIX}/"
fi

cd -
