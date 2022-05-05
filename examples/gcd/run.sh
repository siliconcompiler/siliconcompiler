#!/bin/bash

# Trick to get this script's directory and add it to scpath so that we can run
# this file from project root.
# https://stackoverflow.com/a/246128
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

sc gcd.v \
   -package_version "0.0.0" \
   -package_description "GCD test package" \
   -package_license "MIT" \
   -target "freepdk45_demo" \
   -constraint_file "gcd.sdc" \
   -asic_diearea "(0,0)" \
   -asic_diearea "(100.13,100.8)" \
   -asic_corearea "(10.07,11.2)" \
   -asic_corearea "(90.25,91)" \
   -loglevel "INFO" \
   -quiet \
   -relax \
   -design gcd \
   -track \
   -clean \
   -scpath $SCRIPT_DIR
