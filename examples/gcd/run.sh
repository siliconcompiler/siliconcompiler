#!/bin/sh

OPT=$1
sc examples/gcd/gcd.v \
   -target "asicflow_freepdk45" \
   -constraint "examples/gcd/gcd.sdc" \
   -asic_diearea "(0,0)" \
   -asic_diearea "(100.13,100.8)" \
   -asic_corearea "(10.07,11.2)" \
   -asic_corearea "(90.25,91)" \
   -loglevel "INFO" \
   -quiet \
   -relax \
   -hash \
   -design gcd  $OPT
