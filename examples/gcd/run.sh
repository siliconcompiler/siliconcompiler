#!/bin/bash

# Trick to get this script's directory so that we can run
# this file from project root.
# https://stackoverflow.com/a/246128
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

sc -design gcd \
   $SCRIPT_DIR/gcd.v \
   $SCRIPT_DIR/gcd.sdc \
   -package_version "0.0.0" \
   -package_description "GCD test package" \
   -package_license "MIT" \
   -target "freepdk45_demo" \
   -constraint_outline "(0,0)" \
   -constraint_outline "(100.13,100.8)" \
   -constraint_corearea "(10.07,11.2)" \
   -constraint_corearea "(90.25,91)" \
   -loglevel "INFO" \
   -novercheck \
   -quiet \
   -track \
   -clean
