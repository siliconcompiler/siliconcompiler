#!/bin/sh

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
# Ubuntu 26.04 aarch64: OpenROAD's Qt GUI static link fails on Qt/XCB platform
# libraries that DependencyInstaller.sh does not pull on arm64 (fontconfig,
# xkbcommon, the xcb-* plugin libs and dbus). Install the full set explicitly;
# this is a no-op on x86 where the deps are already present.
sudo apt-get install -y \
    libfontconfig-dev libxkbcommon-dev libxkbcommon-x11-dev libdbus-1-dev \
    libxcb-sync-dev libxcb-xfixes0-dev libxcb-icccm4-dev libxcb-image0-dev \
    libxcb-keysyms1-dev libxcb-randr0-dev libxcb-render-util0-dev \
    libxcb-shape0-dev libxcb-util-dev libxcb-xinerama0-dev libxcb-xkb-dev \
    libxcb-cursor-dev

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

bazelisk run :install --config=release --//:platform=gui --jobs=${NPROC:-$(nproc)} -- "$install_loc"

cd -
