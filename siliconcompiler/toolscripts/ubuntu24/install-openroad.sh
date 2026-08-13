#!/bin/bash

set -ex

src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

sudo apt-get update

sudo apt-get install -y git curl
sudo apt-get install -y make pandoc groff bsdmainutils

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

args=()
if [ ! -z "${SC_BUILD}" ]; then
    # This is a CI build, so build Qt for the baseline x86-64 ISA
    args=(
        --per_file_copt='.*external/qt-bazel.*,-.*qdrawhelper_avx2.*,-.*_ssse3.*,-.*_sse4.*@-march=x86-64'
        --per_file_copt='.*external/qt-bazel.*_ssse3.*@-march=x86-64,-mssse3'
        --per_file_copt='.*external/qt-bazel.*_sse4.*@-march=x86-64,-msse4.1'
        --per_file_copt='.*external/qt-bazel.*qdrawhelper_avx2.*@-march=x86-64-v3'
    )
fi

bazelisk run :install "${args[@]}" --config=release --//:platform=gui --jobs=${NPROC:-$(nproc)} -- "$install_loc"

cd -
