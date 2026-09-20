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
install_prereqs git wget

# RHEL 8 ships python 3.6 as python3, and verilator's build-time code
# generators -- astgen, vlcovgen, bisonpre, flexfix -- use the walrus operator,
# which needs 3.8 or newer. Install a newer interpreter alongside the system one
# rather than displacing it: python3 is what the distribution's own tooling, yum
# included, runs on, and these scripts also call it for _tools.py.
#
# configure picks the interpreter up from PYTHON3 (AC_CHECK_PROG lets the
# environment override the probe) and substitutes it into the makefiles, so
# every generator the build runs uses it. Nothing verilator installs needs it
# afterwards: bin/verilator is perl.
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
    install_prereqs python3.12
    export PYTHON3=python3.12
fi

mkdir -p deps
cd deps

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

wget https://ftp.wayne.edu/gnu/help2man/help2man-1.43.3.tar.gz
tar xvf help2man-1.43.3.tar.gz
cd help2man-1.43.3

./configure $args
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install

cd ..

unset VERILATOR_ROOT

git clone $(python3 ${src_path}/_tools.py --tool verilator --field git-url) verilator
cd verilator
git checkout $(python3 ${src_path}/_tools.py --tool verilator --field git-commit)

autoconf

./configure $args
make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install

cd -
