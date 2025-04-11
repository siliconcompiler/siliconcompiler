#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

sudo yum group install -y "Development Tools"
sudo yum install -y wget git

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

mkdir -p deps
cd deps

wget http://ftp.gnu.org/pub/gnu/gperf/gperf-3.1.tar.gz
tar xvf gperf-3.1.tar.gz
cd gperf-3.1
./configure $args
make -j$(nproc)
sudo make install
cd ..

if [ ! -z ${PREFIX} ]; then
    export PATH="${PREFIX}/bin:$PATH"
    export LD_LIBRARY_PATH="${PREFIX}/lib:$LD_LIBRARY_PATH"
fi

git clone $(python3 ${src_path}/_tools.py --tool icarus --field git-url) icarus
cd icarus
git checkout $(python3 ${src_path}/_tools.py --tool icarus --field git-commit)

sh autoconf.sh
./configure $args
make -j$(nproc)
sudo make install

cd -
