#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

sudo apt-get update

# sby is pure python and drives yosys / yosys-smtbmc (installed separately); its
# 'click' dependency is bundled into the tool prefix below.
sudo apt-get install -y git python3 python3-pip

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool sby --field git-url) sby
cd sby
git checkout $(python3 ${src_path}/_tools.py --tool sby --field git-commit)
$SUDO_INSTALL make install PREFIX="$PREFIX"
cd -

# sby imports 'click' at runtime. The apt python3-click package installs outside
# $PREFIX and is not copied into the combined tool image, so bundle click next
# to sby_core.py (already on sby's sys.path) where it travels with $PREFIX and
# stays importable by whichever python ends up running sby.
$SUDO_INSTALL python3 -m pip install --target "$PREFIX/share/yosys/python3" "click==8.1.7"
