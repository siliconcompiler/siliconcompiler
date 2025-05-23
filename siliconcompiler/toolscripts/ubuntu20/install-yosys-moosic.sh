#!/bin/bash

set -ex

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

sudo apt-get install -y git

git clone $(python3 ${src_path}/_tools.py --tool yosys-moosic --field git-url) yosys-moosic
cd yosys-moosic
git checkout $(python3 ${src_path}/_tools.py --tool yosys-moosic --field git-commit)

make -j$(nproc)
$SUDO_INSTALL make install
cd -
