#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

# Install prerequisites only when they are missing
. "${src_path}/_prereqs.sh"

install_prereqs munge libmunge-dev build-essential libmariadb-dev lbzip2 libjson-c-dev file
install_prereqs libdbus-1-dev

# slurmrestd needs http-parser to build at all -- configure drops the daemon
# without it -- plus libjwt for the auth/jwt mode it uses over TCP and libyaml
# for YAML request bodies. cgroup/v2 needs nothing new here: its gate is
# dbus-1 >= 1.11.16 (above) plus linux/bpf.h, which build-essential already
# brings in through linux-libc-dev.
install_prereqs libhttp-parser-dev libjwt-dev libyaml-dev

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

install_prereqs wget

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

# GCC 15 (Ubuntu 26.04) defaults to C23, where an empty parameter list means
# "takes no arguments"; Slurm's K&R-style function-pointer calls then fail to
# compile. Build against C17 and keep the GCC 14 type checks as warnings.
./configure --enable-slurmrestd CFLAGS="${CFLAGS:-} -std=gnu17 -Wno-error=incompatible-pointer-types -Wno-error=implicit-function-declaration" $cfg_args

make -j${NPROC:-$(nproc)}

$SUDO_INSTALL make install
