#!/bin/sh

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

sudo apt-get install -y build-essential cmake git pkg-config tclsh swig uuid-dev libgoogle-perftools-dev python3 python3-dev
sudo apt-get install -y default-jre

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool surelog --field git-url) surelog
cd surelog

git checkout $(python3 ${src_path}/_tools.py --tool surelog --field git-commit)
git submodule update --init --recursive

# Use clean env for build
python3 -m venv .venv
PYTHON_ROOT=$(realpath .venv)
$PYTHON_ROOT/bin/python -m pip install orderedmultidict
export ADDITIONAL_CMAKE_OPTIONS="-DPython3_ROOT_DIR=$PYTHON_ROOT -DPython3_FIND_STRATEGY=LOCATION"

make
sudo make install

cd -
