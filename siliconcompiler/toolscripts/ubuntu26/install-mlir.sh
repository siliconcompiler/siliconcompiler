#!/bin/bash

# Builds the LLVM/MLIR toolchain that the SODA front end runs on: mlir-opt,
# mlir-translate, llvm-link, opt and clang.
#
# The revision is pinned to the one pnnl/soda-opt is developed and CI'd against
# (see _tools.json). soda-opt is an out-of-tree MLIR project and links against
# MLIR's C++ libraries, so it has to be built against this exact release --
# a distro llvm/mlir package will not do.
#
# The full LLVM install tree is what "sc-install soda" then builds against, so
# this script runs the "install" target rather than only building the four
# binaries the flow calls. That also installs the MLIR test-pass libraries
# (MLIRLinalgTestPasses and friends) which soda-opt links against.
#
# clang is built alongside mlir because the flow compiles the MLIR runtime
# helpers to LLVM IR before linking them into a kernel, and that IR has to be
# readable by the same llvm-link. Taking it from this build rather than from the
# distribution keeps the two in step, at the cost of a longer build.
#
# This is a large build: expect one to two hours on a well provisioned machine
# and several GB of disk in the install prefix.

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

install_prereqs git build-essential ninja-build python3 python3-venv \
    zlib1g-dev libzstd-dev

mkdir -p deps
cd deps

# LLVM 19 needs cmake >= 3.20; ubuntu20 ships 3.16, so the version is pinned
# here for every ubuntu the same way install-opensta.sh does it.
python3 -m venv .mlir --clear
. .mlir/bin/activate
python3 -m pip install cmake==3.31.6

version=$(python3 "${src_path}/_tools.py" --tool mlir --field git-commit)

git clone --depth=1 --branch "${version}" \
    "$(python3 "${src_path}/_tools.py" --tool mlir --field git-url)" llvm-project

if [ ! -z ${PREFIX} ]; then
    install_dir="$PREFIX"
else
    install_dir=/opt/mlir
    SUDO_INSTALL=sudo

    $SUDO_INSTALL mkdir -p "${install_dir}"
    $SUDO_INSTALL chown "$USER:$USER" "${install_dir}"
fi

# lld cuts the link time and, more importantly, the link memory of an MLIR
# build substantially, but it is not worth failing the install over.
lld_args=
if command -v ld.lld > /dev/null 2>&1; then
    lld_args=-DLLVM_ENABLE_LLD=ON
fi

# ubuntu26 defaults to gcc 15, which no longer pulls <cstdint> in transitively
# from the other standard headers. LLVM 19.1.5 predates that and does not include
# it where it uses int64_t, so the build dies in the affine dialect with
#   ValueBoundsOpInterfaceImpl.h:31:11: error: 'int64_t' was not declared in this scope
# Forcing the header into every C++ translation unit is what upstream ended up
# doing file by file after this release. Only ubuntu26 needs it -- ubuntu24 and
# earlier default to a gcc old enough to still include it.
cmake -G Ninja \
    -S llvm-project/llvm \
    -B build \
    -DCMAKE_INSTALL_PREFIX="${install_dir}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS="-include cstdint" \
    -DLLVM_ENABLE_PROJECTS="mlir;clang" \
    -DLLVM_TARGETS_TO_BUILD=host \
    -DLLVM_ENABLE_ASSERTIONS=OFF \
    -DLLVM_BUILD_EXAMPLES=OFF \
    -DLLVM_INCLUDE_BENCHMARKS=OFF \
    -DLLVM_INCLUDE_DOCS=OFF \
    -DLLVM_OPTIMIZED_TABLEGEN=ON \
    -DLLVM_PARALLEL_LINK_JOBS=2 \
    -DMLIR_ENABLE_BINDINGS_PYTHON=OFF \
    -DLLVM_INSTALL_UTILS=ON \
    ${lld_args}

# The tools the SODA flow drives directly, built first so a failure in one of
# them is reported before the rest of the install tree is produced.
cmake --build build --target opt llvm-link clang mlir-opt mlir-translate \
    -j${NPROC:-$(nproc)}

# Everything soda-opt needs to configure and link against.
cmake --build build --target install -j${NPROC:-$(nproc)}

cd -

if [ -z ${PREFIX} ]; then
    echo "Please add \"export PATH=\"/opt/mlir/bin:\$PATH\"\" to your .bashrc"
fi
