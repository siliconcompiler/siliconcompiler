#!/bin/sh

set -ex

src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

sudo yum install -y git curl --skip-broken
sudo yum install -y make pandoc groff util-linux --skip-broken

mkdir -p deps
cd deps

mkdir -p bazelbin/bin
BAZEL_PREFIX=$(pwd)/bazelbin

PATH="$BAZEL_PREFIX/bin:$PATH"

git clone $(python3 ${src_path}/_tools.py --tool openroad --field git-url) openroad
cd openroad
git checkout $(python3 ${src_path}/_tools.py --tool openroad --field git-commit)
git submodule update --init --recursive

sudo ./etc/DependencyInstaller.sh -bazel -prefix="$BAZEL_PREFIX"
sudo chown -R $USER:$USER $BAZEL_PREFIX

if [ ! -z ${PREFIX} ]; then
    install_loc="$PREFIX"
else
    install_loc="$HOME/.local"
fi

bazelisk run :install --config=release --//:platform=gui -- "$install_loc"

cd -
