#!/bin/sh

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

mkdir -p deps
cd deps

curl -sSL https://get.haskellstack.org/ | sh

git clone $(python3 ${src_path}/_tools.py --tool sv2v --field git-url) sv2v
cd sv2v
git checkout $(python3 ${src_path}/_tools.py --tool sv2v --field git-commit)

make

cd -
