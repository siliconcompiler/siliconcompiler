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

install_prereqs wget

# sbt is a launcher script for a JVM tool, so a JRE is a runtime requirement and
# not just a build one. It used to arrive by accident: install-surelog.sh pulls a
# JRE in to run ANTLR's parser generator, and that leaked into the container
# image through apt.txt. Declare it here so that dropping surelog's build-time
# JRE cannot leave chisel without a java to run.
install_prereqs default-jre-headless

mkdir -p deps
cd deps

version=$(python3 ${src_path}/_tools.py --tool chisel --field version)

wget -O sbt.tgz https://github.com/sbt/sbt/releases/download/v${version}/sbt-${version}.tgz

args=
if [ ! -z ${PREFIX} ]; then
    args="-C $PREFIX --strip-components 1"
fi

# sbt ships a native "sbtn" client for every platform it supports, so the
# tarball carries macOS, Windows and aarch64 binaries that will never run here
# -- about 127MB of the install. Skip them at extraction time rather than
# deleting them afterwards: PREFIX is often a shared prefix (sc-install defaults
# to ~/.local) and this script should never remove a file it did not write.
#
# An unrecognised machine keeps every launcher, and a platform sbt adds later is
# extracted rather than dropped. Both cost size only.
case "$(uname -m)" in
    x86_64|amd64)  keep_sbtn=sbtn-x86_64-pc-linux ;;
    aarch64|arm64) keep_sbtn=sbtn-aarch64-pc-linux ;;
    *)             keep_sbtn= ;;
esac

sbtn_excludes=
if [ -n "${keep_sbtn}" ]; then
    for sbtn in sbtn-x86_64-pc-linux sbtn-aarch64-pc-linux \
                sbtn-universal-apple-darwin sbtn-x86_64-pc-win32.exe; do
        if [ "${sbtn}" != "${keep_sbtn}" ]; then
            sbtn_excludes="${sbtn_excludes} --exclude=*/${sbtn}"
        fi
    done
fi

$SUDO_INSTALL tar xvf sbt.tgz $sbtn_excludes $args

cd -

if [ -z ${PREFIX} ]; then
    echo "Please add \"export PATH="${src_path}/deps/sbt/bin:\$PATH"\" to your .bashrc"
fi
