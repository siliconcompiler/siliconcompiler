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

sudo apt-get install -y git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool yosys-parmys --field git-url) yosys-parmys
cd yosys-parmys
git checkout $(python3 ${src_path}/_tools.py --tool yosys-parmys --field git-commit)
git submodule update --init --recursive

# apply patch
cat > build_patch <<EOF
diff --git a/parmys/parmys-plugin/Makefile b/parmys/parmys-plugin/Makefile
index dbb3eb11e..cb85631bc 100644
--- a/parmys/parmys-plugin/Makefile
+++ b/parmys/parmys-plugin/Makefile
@@ -49,7 +49,7 @@ VTR_INSTALL_DIR ?= /usr/local
 
 include ../Makefile_plugin.common
 
-CXXFLAGS += -std=c++14 -Wall -W -Wextra \\
+CXXFLAGS += -std=c++17 -Wall -W -Wextra \\
             -Wno-deprecated-declarations \\
             -Wno-unused-parameter \\
             -I. \\
diff --git a/parmys/parmys-plugin/parmys_update.cc b/parmys/parmys-plugin/parmys_update.cc
index ef55213c5..4e4d6dd15 100644
--- a/parmys/parmys-plugin/parmys_update.cc
+++ b/parmys/parmys-plugin/parmys_update.cc
@@ -506,9 +506,9 @@ void define_logical_function_yosys(nnode_t *node, Module *module)
         lutptr = &cell->parameters.at(ID::LUT);
         for (int i = 0; i < (1 << node->num_input_pins); i++) {
             if (i == 3 || i == 5 || i == 6 || i == 7) //"011 1\n101 1\n110 1\n111 1\n"
-                lutptr->bits.at(i) = RTLIL::State::S1;
+                lutptr->bits().at(i) = RTLIL::State::S1;
             else
-                lutptr->bits.at(i) = RTLIL::State::S0;
+                lutptr->bits().at(i) = RTLIL::State::S0;
         }
     } else {
         cell->parameters[ID::A_WIDTH] = RTLIL::Const(int(node->num_input_pins));
EOF

git apply build_patch

export VTR_INSTALL_DIR=$(dirname $(which vpr))/..
YOSYS_PLUGIN=$(yosys-config --datdir)/plugins/

cd parmys

make -j$(nproc)
$SUDO_INSTALL mkdir -p $YOSYS_PLUGIN
$SUDO_INSTALL cp parmys-plugin/build/parmys.so $YOSYS_PLUGIN
cd -
