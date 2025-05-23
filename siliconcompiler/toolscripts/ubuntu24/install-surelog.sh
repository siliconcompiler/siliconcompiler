#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

# These dependencies are up-to-date with instructions from the INSTALL.md from the commit we are pinned to below
sudo apt-get install -y build-essential cmake git pkg-config \
    tclsh swig uuid-dev libgoogle-perftools-dev python3 \
    python3-orderedmultidict python3-psutil python3-dev \
    default-jre lcov zlib1g-dev

sudo apt-get install -y git

mkdir -p deps
cd deps

python3 -m venv .surelog --clear
. .surelog/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install cmake==3.31.6
python3 -m pip install orderedmultidict

git clone $(python3 ${src_path}/_tools.py --tool surelog --field git-url) surelog
cd surelog
git checkout $(python3 ${src_path}/_tools.py --tool surelog --field git-commit)
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
