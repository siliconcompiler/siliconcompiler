#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

mkdir -p deps
cd deps

sudo apt-get install -y build-essential curl git libssl-dev openssl pkg-config

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s - -y
export PATH="$HOME/.cargo/bin:$PATH"

git clone $(python3 ${src_path}/_tools.py --tool surfer --field git-url) surfer
cd surfer
git checkout $(python3 ${src_path}/_tools.py --tool surfer --field git-commit)
git submodule update --init

cargo fetch --locked
cargo build -j $(nproc) --frozen --release

if [ ! -z ${PREFIX} ]; then
    $SUDO_INSTALL install -Dm00755 target/release/surfer -t ${PREFIX}/bin
fi
