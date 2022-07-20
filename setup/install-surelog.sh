#!/bin/sh

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)

sudo apt-get install -y build-essential cmake git pkg-config tclsh swig uuid-dev libgoogle-perftools-dev python3 python3-dev
sudo apt-get install -y default-jre

cd ${src_path}/..
git submodule update --init --recursive third_party/tools/surelog
cd third_party/tools/surelog

# Workaround: Surelog's antlr4 dependency clones a git:// repo during its build process.
# GitHub recently deprecated some ways of cloning via git://, so we need to use https:// instead.
# We don't want to overwrite the user's global git config, so use $HOME to set global search path.
# In git v2.32+, we'll be able to use $GIT_CONFIG_GLOBAL, but not many systems will support that.
git config --file $(pwd)/.gitconfig url."https://".insteadOf git://
export HOME=$(pwd)

make
sudo make install
cd -
