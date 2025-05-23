#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

sudo yum group install -y "Development Tools"
sudo yum install -y gtk3-devel \
    bzip2-devel xz-devel tcl-devel tk-devel
sudo yum install -y wget git
sudo dnf config-manager --set-enabled devel || true
sudo yum install -y Judy-devel
sudo dnf config-manager --set-disabled devel || true

mkdir -p deps
cd deps

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

wget http://ftp.gnu.org/pub/gnu/gperf/gperf-3.1.tar.gz
tar xvf gperf-3.1.tar.gz
cd gperf-3.1
./configure $args
make -j$(nproc)
$SUDO_INSTALL make install
cd ..

git clone $(python3 ${src_path}/_tools.py --tool gtkwave --field git-url) gtkwave
cd gtkwave
git checkout $(python3 ${src_path}/_tools.py --tool gtkwave --field git-commit)

cd gtkwave3-gtk3

./autogen.sh
LDFLAGS="-ltcl -ltk" ./configure --enable-gtk3 $args
make -j$(nproc)
$SUDO_INSTALL make install
