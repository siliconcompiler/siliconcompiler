#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1; pwd -P)/..

sudo apt-get install -y openssl libssl-dev cargo

sudo apt-get install -y git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool surfer --field git-url) gtkwave
cd surfer
git checkout $(python3 ${src_path}/_tools.py --tool surfer --field git-commit)

cargo fetch --locked
cargo build -j $(nproc) --frozen --release

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

if [ ! -z ${PREFIX} ]; then
    $SUDO_INSTALL install -Dm00755 target/release/surfer -t ${PREFIX}/bin
fi
