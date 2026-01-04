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

sudo apt-get install -y build-essential libfl-dev

# From: https://github.com/keplertech/kepler-formal/blob/ea6b0ce62f6f8fd2327e79913a07c74a3210551d/README.md
sudo apt-get install -y g++ libboost-dev python3-dev capnproto libcapnp-dev libtbb-dev \
    pkg-config bison flex doxygen libspdlog-dev libfmt-dev libboost-iostreams-dev zlib1g-dev

sudo apt-get install -y git

mkdir -p deps
cd deps

python3 -m venv .keplerformal --clear
. .keplerformal/bin/activate
python3 -m pip install cmake==3.31.6

git clone $(python3 ${src_path}/_tools.py --tool keplerformal --field git-url) keplerformal
cd keplerformal
git checkout $(python3 ${src_path}/_tools.py --tool keplerformal --field git-commit)
git submodule update --init --recursive

git apply - <<EOF
diff --git a/CMakeLists.txt b/CMakeLists.txt
index 65d0d04..a67d38f 100644
--- a/CMakeLists.txt
+++ b/CMakeLists.txt
@@ -26,9 +26,9 @@ add_subdirectory(thirdparty)
 
 # option(ENABLE_UNIT_TESTS ON)
 # if(ENABLE_UNIT_TESTS)
-include(CTest)
-enable_testing()
-add_subdirectory(test)
+# include(CTest)
+# enable_testing()
+# add_subdirectory(test)
 # endif()
 
 option(CODE_COVERAGE "Enable coverage reporting" OFF)
EOF

cmake_args=""
if [ ! -z ${PREFIX} ]; then
    cmake_args="-DCMAKE_INSTALL_PREFIX=$PREFIX"
fi

mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS_RELEASE="-Ofast -march=native -ffast-math -flto" \
    -DCMAKE_EXE_LINKER_FLAGS="-flto" \
	-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=TRUE \
    $cmake_args
make -j$(nproc)
$SUDO_INSTALL make install

cd -
