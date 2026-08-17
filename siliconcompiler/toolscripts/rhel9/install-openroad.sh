#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

# Install prerequisites only when they are missing
. "${src_path}/_prereqs.sh"

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

install_prereqs --skip-broken git curl
install_prereqs --skip-broken make pandoc groff util-linux

# Extracted from OpenROAD's etc/DependencyInstaller.sh (_install_bazel), which
# this script used to run under sudo and then chown the prefix back, because
# root had created files in a build directory we already own. With -bazel and no
# -all/-base/-common that function is the whole payload, and it splits cleanly:
# package installs (below, conditional on being missing) and the bazelisk
# download (further down, no root at all).
#
# Runtime libraries for the prebuilt LLVM toolchain that the Bazel build pulls
# in (lld links against libxml2 and ncurses).
install_prereqs glibc-devel libxml2 ncurses-libs zlib libstdc++

# xcb/X11 libraries for the GUI build. The -devel ones live in Rocky 9's
# CodeReady Builder (CRB) repository, which is disabled by default, so enabling
# it is root-only work whose only purpose is this install -- it belongs inside
# the same conditional (epel-release, installed in the base image, ships the
# /usr/bin/crb helper).
gui_pkgs="libxcb-devel xcb-util-devel xcb-util-image-devel \
    xcb-util-keysyms-devel xcb-util-renderutil-devel xcb-util-wm-devel \
    libX11-xcb libX11 libSM libICE xcb-util-cursor libxcb \
    dbus-libs fontconfig libxkbcommon libxkbcommon-x11"
if prereqs_missing $gui_pkgs; then
    sudo /usr/bin/crb enable || sudo dnf config-manager --set-enabled crb
    install_prereqs $gui_pkgs
fi

mkdir -p deps
cd deps

mkdir -p bazelbin/bin
BAZEL_PREFIX=$(pwd)/bazelbin

PATH="$BAZEL_PREFIX/bin:$PATH"

git clone $(python3 ${src_path}/_tools.py --tool openroad --field git-url) openroad
cd openroad
git checkout $(python3 ${src_path}/_tools.py --tool openroad --field git-commit)
git submodule update --init --recursive

# Install the bazelisk launcher into the build directory we own, so it needs no
# root at all. Read the version and checksum out of the OpenROAD checkout rather
# than pinning them here, so they follow the pinned commit instead of drifting
# from it.
if ! command -v bazelisk > /dev/null 2>&1; then
    dep_installer=etc/DependencyInstaller.sh
    case "$(uname -m)" in
        aarch64) bazelisk_arch=arm64 ;;
        *) bazelisk_arch=amd64 ;;
    esac
    bazelisk_version=$(sed -n 's/^BAZELISK_VERSION="\([^"]*\)".*/\1/p' "$dep_installer")
    bazelisk_md5=$(sed -n "s/^BAZELISK_CHECKSUM_$(echo $bazelisk_arch | tr a-z A-Z)=\"\([^\"]*\)\".*/\1/p" "$dep_installer")
    if [ -z "$bazelisk_version" ] || [ -z "$bazelisk_md5" ]; then
        echo "Could not read the bazelisk version/checksum from $dep_installer" >&2
        exit 1
    fi

    curl -fL -o bazelisk \
        "https://github.com/bazelbuild/bazelisk/releases/download/v${bazelisk_version}/bazelisk-linux-${bazelisk_arch}"
    echo "${bazelisk_md5}  bazelisk" | md5sum --quiet -c -
    chmod +x bazelisk
    mv bazelisk "$BAZEL_PREFIX/bin/bazelisk"
fi

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
