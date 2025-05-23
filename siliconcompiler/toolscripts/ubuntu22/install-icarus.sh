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

sudo apt-get install -y build-essential bison flex gperf libreadline-dev libncurses-dev

sudo apt-get install -y git automake autoconf

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool icarus --field git-url) icarus
cd icarus
git checkout $(python3 ${src_path}/_tools.py --tool icarus --field git-commit)

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

sh autoconf.sh
./configure $args
make -j$(nproc)
$SUDO_INSTALL make install
