#!/bin/sh

OPT=$1

echo $OPT
sc gcd.v \
   -target "asap7_demo" \
   -constraint "gcd.sdc" \
   -asic_diearea "(0,0)" \
   -asic_diearea "(100.13,100.8)" \
   -asic_corearea "(10.07,11.2)" \
   -asic_corearea "(90.25,91)" \
   -pdk_wafersize "300.0" \
   -loglevel "INFO" \
   -quiet \
   -relax \
   -design gcd $OPT
