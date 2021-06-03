#!/bin/sh

OPT=$1
sc examples/gcd/gcd.v \
   -target "skywater130" \
   -constraint "examples/gcd/gcd.sdc" \
   -asic_diesize "0 0 200.56 201.28" \
   -asic_coresize "20.24 21.76 180.32 184.96" \
   -loglevel "INFO" \
   -quiet \
   -design gcd  $OPT
