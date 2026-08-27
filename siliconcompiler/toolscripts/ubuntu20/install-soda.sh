#!/bin/bash

# Builds PNNL's soda-opt, the MLIR front end of the SODA Synthesizer, which
# provides the soda-opt and soda-translate binaries.
#
# soda-opt is an out-of-tree MLIR project: it links against MLIR's C++
# libraries and has to be built against the same llvm-project revision it was
# developed on. That revision is what "sc-install mlir" installs, so run that
# first -- this script looks for the resulting MLIR install tree and stops with
# an explanation if it is not there.

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

# Locate the MLIR install tree installed by install-mlir.sh. MLIR_PREFIX wins,
# then the prefix this install is going into, then the unprefixed default of
# install-mlir.sh, then whatever mlir-opt on PATH belongs to.
mlir_on_path=
if command -v mlir-opt > /dev/null 2>&1; then
    mlir_on_path=$(dirname "$(dirname "$(command -v mlir-opt)")")
fi

mlir_prefix=
for candidate in "${MLIR_PREFIX}" "${PREFIX}" /opt/mlir "${mlir_on_path}"; do
    if [ -n "${candidate}" ] && [ -d "${candidate}/lib/cmake/mlir" ]; then
        mlir_prefix="${candidate}"
        break
    fi
done

if [ -z "${mlir_prefix}" ]; then
    echo "ERROR: no MLIR install tree found." >&2
    echo "soda-opt builds against MLIR's C++ libraries, which are installed by:" >&2
    echo "    sc-install mlir" >&2
    echo "Set MLIR_PREFIX to point at an existing install to use that instead." >&2
    exit 1
fi
echo "Using MLIR install tree: ${mlir_prefix}"

mkdir -p deps
cd deps

python3 -m venv .soda --clear
. .soda/bin/activate
python3 -m pip install cmake==3.31.6

git clone "$(python3 "${src_path}/_tools.py" --tool soda --field git-url)" soda-opt
cd soda-opt
git checkout "$(python3 "${src_path}/_tools.py" --tool soda --field git-commit)"
cd -

if [ ! -z ${PREFIX} ]; then
    install_dir="$PREFIX"
else
    install_dir=/opt/soda
    SUDO_INSTALL=sudo

    $SUDO_INSTALL mkdir -p "${install_dir}/bin"
    $SUDO_INSTALL chown -R "$USER:$USER" "${install_dir}"
fi

cmake -G Ninja \
    -S soda-opt \
    -B build \
    -DCMAKE_INSTALL_PREFIX="${install_dir}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DMLIR_DIR="${mlir_prefix}/lib/cmake/mlir" \
    -DLLVM_DIR="${mlir_prefix}/lib/cmake/llvm" \
    -DLLVM_EXTERNAL_LIT="${mlir_prefix}/bin/llvm-lit" \
    -DMLIR_ENABLE_BINDINGS_PYTHON=OFF

cmake --build build --target soda-opt soda-translate -j${NPROC:-$(nproc)}

# Install only the two binaries the flow drives. "cmake --install" would also
# want the targets this build deliberately skipped (the python modules, the
# llvm plugins and the lit test suite).
mkdir -p "${install_dir}/bin"
for binary in soda-opt soda-translate; do
    install -m 755 "build/bin/${binary}" "${install_dir}/bin/${binary}"
done

cd -

if [ -z ${PREFIX} ]; then
    echo "Please add \"export PATH=\"/opt/soda/bin:\$PATH\"\" to your .bashrc"
fi
