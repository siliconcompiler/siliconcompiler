#!/bin/sh

set -ex

sudo apt-get install -y munge libmunge-dev build-essential libmariadb-dev lbzip2 libjson-c-dev
sudo apt-get install -y libdbus-1-dev

sudo apt-get install -y wget

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

mkdir -p deps
cd deps

pkg_version=$(python3 ${src_path}/_tools.py --tool slurm --field version)

# Build and install Slurm
wget -O slurm.tar.bz2 https://download.schedmd.com/slurm/slurm-${pkg_version}.tar.bz2
mkdir -p slurm
tar xvf slurm.tar.bz2 --strip-components=1 -C slurm

cd slurm

cfg_args=""
if [ ! -z ${PREFIX} ]; then
    cfg_args="--prefix=$PREFIX"
fi

./configure $cfg_args

make -j$(nproc)

$SUDO_INSTALL make install
