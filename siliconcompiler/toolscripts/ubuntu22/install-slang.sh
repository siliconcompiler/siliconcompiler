#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo apt-get install -y git build-essential

mkdir -p deps
cd deps

python3 -m venv .slang --clear
. .slang/bin/activate
python3 -m pip install cmake==3.31.6

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

git clone $(python3 ${src_path}/_tools.py --tool slang --field git-url) slang
cd slang
git checkout $(python3 ${src_path}/_tools.py --tool slang --field git-commit)

cfg_args=""
if [ ! -z ${PREFIX} ]; then
    cfg_args="-D CMAKE_INSTALL_PREFIX=$PREFIX"
fi

cmake -B build $cfg_args
cmake --build build -j$(nproc)
$SUDO_INSTALL make -C build install

cd -
