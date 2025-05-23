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

version=$(python3 ${src_path}/_tools.py --tool chisel --field version)

wget -O sbt.tgz https://github.com/sbt/sbt/releases/download/v${version}/sbt-${version}.tgz

args=
if [ ! -z ${PREFIX} ]; then
    args="-C $PREFIX --strip-components 1"
fi

$SUDO_INSTALL tar xvf sbt.tgz $args

cd -

if [ -z ${PREFIX} ]; then
    echo "Please add \"export PATH="${src_path}/deps/sbt/bin:\$PATH"\" to your .bashrc"
fi
