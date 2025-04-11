#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo yum group install -y "Development Tools" --exclude "python3*" --skip-broken
sudo dnf config-manager --set-enabled devel || true
sudo yum install -y boost boost-python3-devel cmake python-devel
dnf config-manager --set-disabled devel || true

sudo yum install -y git

mkdir -p deps
cd deps

if [ -z ${PREFIX} ]; then
    PREFIX=~/.local
fi

# Download XDM
git clone $(python3 ${src_path}/_tools.py --tool xdm --field git-url) xdm
cd xdm
git checkout $(python3 ${src_path}/_tools.py --tool xdm --field git-commit)

mkdir -p build
cd build

python3 -m venv venv
. ./venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install PyInstaller

args=
if [ ! -z ${PREFIX} ]; then
    args="-DCMAKE_INSTALL_PREFIX=$PREFIX"
fi

cmake .. $args
make -j$(nproc)

sudo make install

cd -
