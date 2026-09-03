#!/bin/bash

# Builds the LLVM/MLIR toolchain that the SODA front end runs on: mlir-opt,
# mlir-translate, llvm-link, opt and clang.
#
# The revision is pinned to the one pnnl/soda-opt is developed and CI'd against
# (see _tools.json). soda-opt is an out-of-tree MLIR project and links against
# MLIR's C++ libraries, so it has to be built against this exact release --
# a distro llvm/mlir package will not do.
#
# The LLVM dev tree -- headers, static libraries and cmake exports -- is what
# "sc-install soda" then builds against, so the install has to carry more than
# the five binaries the flow calls. It does not have to carry everything, and it
# no longer does: LLVM_DISTRIBUTION_COMPONENTS below declares the set, which is
# what trims 2.1GB of unused tools out of the install tree. See the comment on
# that variable.
#
# One thing to watch across LLVM bumps: soda-opt links against the MLIR
# test-pass libraries (MLIRLinalgTestPasses and friends), which are built
# because LLVM_INCLUDE_TESTS defaults on. If a bump stops the mlir-libraries
# component covering them, soda-opt fails to link and the fix is to name those
# libraries in the component list.
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

if [ -n "${PREFIX:-}" ]; then
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

# What gets installed. LLVM_DISTRIBUTION_COMPONENTS narrows the install to a
# declared set and generates an "install-distribution" target for it, which is
# how LLVM itself expects a packager to trim an install tree -- rather than
# installing everything and deleting afterwards, which would mean this script
# removing files from a prefix it may share with every other SC tool.
#
# Two groups, for the project's two consumers:
#
#   the flow drives clang, opt, llvm-link, mlir-opt and mlir-translate, and
#   nothing else (each is named in a set_exe call under
#   siliconcompiler/tools/{mlir,soda}/)
#
#   install-soda.sh then builds soda-opt against this tree, which needs the
#   headers, the static libraries and the cmake exports of all three projects,
#   plus the tablegen tools -- soda-opt is an out-of-tree dialect and generates
#   its headers from .td files. MLIRConfig.cmake names exactly three
#   executables, and these are they:
#
#       MLIR_TABLEGEN_EXE             mlir-tblgen
#       MLIR_PDLL_TABLEGEN_EXE        mlir-pdll
#       MLIR_SRC_SHARDER_TABLEGEN_EXE mlir-src-sharder   (not installable)
#
#   The first two are here. mlir-src-sharder is not: it has no install target at
#   all, so naming it fails configure -- the same quirk as llvm-lit above, where
#   MLIRConfig advertises a path the install never provides.
#
#   Leaving mlir-tblgen out does not fail configure, which is what made its
#   absence expensive to find: MLIRConfig sets the variable to a bare name
#   either way, and the build only falls over later, when ninja looks for a file
#   called "mlir-tblgen" next to the generated header. mlir-pdll is included on
#   the same reasoning; soda does not use PDLL today, and a project that did
#   would break the same silent way.
#
# Note that llvm-lit is deliberately absent even though install-soda.sh passes
# -DLLVM_EXTERNAL_LIT=${mlir_prefix}/bin/llvm-lit. llvm-lit has no install rule
# at all -- llvm/utils/llvm-lit only configure_file()s it into the build tree --
# so that path has never existed in the prefix, under this install or the plain
# "install" target before it. cmake only reads LLVM_EXTERNAL_LIT to run the lit
# suite, which this build does not, so the dangling path is harmless. Listing
# llvm-lit as a component is not: it fails configure outright.
#
# A name with no install target is a configure-time SEND_ERROR from
# LLVMDistributionSupport.cmake naming the component, so a mistake here fails in
# seconds rather than after the build. If a future LLVM bump drops one of these,
# that error says which.
distribution_components="clang;opt;llvm-link;mlir-opt;mlir-translate;llvm-config"
distribution_components="${distribution_components};mlir-tblgen;mlir-pdll"
distribution_components="${distribution_components};llvm-headers;llvm-libraries;cmake-exports"
distribution_components="${distribution_components};clang-headers;clang-libraries;clang-cmake-exports"
distribution_components="${distribution_components};clang-resource-headers"
distribution_components="${distribution_components};mlir-headers;mlir-libraries;mlir-cmake-exports"
distribution_components="${distribution_components};FileCheck;count;not"

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
    -DLLVM_DISTRIBUTION_COMPONENTS="${distribution_components}" \
    ${lld_args}

# The tools the SODA flow drives directly, built first so a failure in one of
# them is reported before the rest of the install tree is produced.
cmake --build build --target opt llvm-link clang mlir-opt mlir-translate \
    -j${NPROC:-$(nproc)}

# Install only the declared distribution. The plain "install" target ships 111
# binaries beyond the five the flow drives -- clang-repl at 141MB,
# mlir-cpu-runner at 110MB, mlir-lsp-server at 95MB, bugpoint, lli, llvm-lto and
# the rest, 2.1GB in total -- and none of them is ever invoked.
cmake --build build --target install-distribution -j${NPROC:-$(nproc)}

cd -

if [ -z "${PREFIX:-}" ]; then
    echo "Please add \"export PATH=\"/opt/mlir/bin:\$PATH\"\" to your .bashrc"
fi
