#!/bin/sh

sc -design gcd \
   -source "verilog gcd.v" \
   -source "sdc gcd.sdc" \
   -package_version "0.0.0" \
   -package_description "GCD test package" \
   -package_license "MIT" \
   -target "arap7_demo" \
   -asic_diearea "(0,0)" \
   -asic_diearea "(100.13,100.8)" \
   -asic_corearea "(10.07,11.2)" \
   -asic_corearea "(90.25,91)" \
   -loglevel "INFO" \
   -novercheck \
   -quiet \
   -relax \
   -track \
   -clean \
