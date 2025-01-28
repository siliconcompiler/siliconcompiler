#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

mkdir -p deps
cd deps

python3 -m venv .slang --clear
. .slang/bin/activate
python3 -m pip install cmake

git clone $(python3 ${src_path}/_tools.py --tool slang --field git-url) slang
cd slang
git checkout $(python3 ${src_path}/_tools.py --tool slang --field git-commit)

cfg_args=""
if [ ! -z ${PREFIX} ]; then
    cfg_args="--prefix=$PREFIX"
fi

cmake -B build
cmake --build build -j$(nproc)
cmake --install build --strip $cfg_args

cd -
