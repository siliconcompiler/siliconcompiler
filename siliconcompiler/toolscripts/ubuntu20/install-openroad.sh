#!/bin/sh

set -ex

src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL="sudo -E PATH=$PATH"
else
    SUDO_INSTALL=""
fi

sudo apt-get update

sudo apt-get install -y git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool openroad --field git-url) openroad
cd openroad
git checkout $(python3 ${src_path}/_tools.py --tool openroad --field git-commit)
git submodule update --init --recursive

git apply - <<EOF
diff --git a/CMakeLists.txt b/CMakeLists.txt
index de6a3cb472..c68d47da4e 100644
--- a/CMakeLists.txt
+++ b/CMakeLists.txt
@@ -62,7 +62,7 @@ list(APPEND CMAKE_MODULE_PATH "\${CMAKE_CURRENT_SOURCE_DIR}/cmake")
 # Get version string in OPENROAD_VERSION
 if(NOT OPENROAD_VERSION)
   include(GetGitRevisionDescription)
-  git_describe(OPENROAD_VERSION)
+  git_describe(OPENROAD_VERSION --match "v[0-9]*")
   string(FIND \${OPENROAD_VERSION} "NOTFOUND" GIT_DESCRIBE_NOTFOUND)
   if(\${GIT_DESCRIBE_NOTFOUND} GREATER -1)
     message(WARNING "OpenROAD git describe failed, using sha1 instead")
EOF

deps_args=""
if [ ! -z ${PREFIX} ]; then
    deps_args="-prefix=$PREFIX"
fi
sudo ./etc/DependencyInstaller.sh -base
sudo rm -f etc/openroad_deps_prefixes.txt
$SUDO_INSTALL ./etc/DependencyInstaller.sh -common $deps_args

cmake_args="-DENABLE_TESTS=OFF"
if [ ! -z ${PREFIX} ]; then
    cmake_args="$cmake_args -DCMAKE_INSTALL_PREFIX=$PREFIX"
fi

./etc/Build.sh -cmake="$cmake_args" -threads=${NPROC:-$(nproc)}

cd build
$SUDO_INSTALL make install

cd -
