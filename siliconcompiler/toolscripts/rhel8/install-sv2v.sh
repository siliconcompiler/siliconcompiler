#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

mkdir -p deps
cd deps

sudo yum group install -y "Development Tools"
sudo yum install -y gmp-devel xz

curl -sSL https://get.haskellstack.org/ | sh -s - -f

git clone $(python3 ${src_path}/_tools.py --tool sv2v --field git-url) sv2v
cd sv2v
git checkout $(python3 ${src_path}/_tools.py --tool sv2v --field git-commit)

make -j$(nproc)

if [ ! -z ${PREFIX} ]; then
    sudo mkdir -p ${PREFIX}/bin/
    sudo cp bin/* ${PREFIX}/bin/
fi

cd -
