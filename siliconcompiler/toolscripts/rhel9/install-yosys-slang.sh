#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo yum install -y git

mkdir -p deps
cd deps

python3 -m venv .yosys-slang --clear
. .yosys-slang/bin/activate
python3 -m pip install cmake==3.31.6

git clone $(python3 ${src_path}/_tools.py --tool yosys-slang --field git-url) yosys-slang
cd yosys-slang
git checkout $(python3 ${src_path}/_tools.py --tool yosys-slang --field git-commit)
git submodule update --init --recursive

make -j$(nproc)

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

$SUDO_INSTALL make install
cd -
