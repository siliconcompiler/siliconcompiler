#!/bin/sh

set -e

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

mkdir -p deps
cd deps

version=$(python3 ${src_path}/_tools.py --tool verible --field version)
filename=verible-$version-linux-static-x86_64.tar.gz

wget https://github.com/chipsalliance/verible/releases/download/$version/$filename

tar xzf $filename

if [ -z ${PREFIX} ]; then
    PREFIX=/opt/verible
    sudo mkdir -p $PREFIX
    echo "Please add \"export PATH="/opt/verible/bin:\$PATH"\" to your .bashrc"
fi

sudo mv verible-$version/* $PREFIX
