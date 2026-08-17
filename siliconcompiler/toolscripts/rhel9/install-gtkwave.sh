#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

# Install prerequisites only when they are missing
. "${src_path}/_prereqs.sh"

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

install_prereq_group "Development Tools"
install_prereqs gtk3-devel gperf \
    bzip2-devel xz-devel tcl-devel tk-devel
install_prereqs wget git
# The 'devel' repository is disabled by default. Enabling and disabling it is
# root-only work whose only purpose is the install between them, so the whole
# block is skipped when those packages are already present.
if prereqs_missing Judy-devel; then
    sudo dnf config-manager --set-enabled devel || true
    install_prereqs Judy-devel
    sudo dnf config-manager --set-disabled devel || true
fi

mkdir -p deps
cd deps

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

git clone $(python3 ${src_path}/_tools.py --tool gtkwave --field git-url) gtkwave
cd gtkwave
git checkout $(python3 ${src_path}/_tools.py --tool gtkwave --field git-commit)

cd gtkwave3-gtk3

./autogen.sh
LDFLAGS="-ltcl -ltk" ./configure --enable-gtk3 $args
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install
