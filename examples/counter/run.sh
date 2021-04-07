#!/bin/sh
sc examples/counter/counter.v \
   -pdk_rev "1.0" \
   -target "freepdk45" \
   -asic_diesize "0 0 100.13 100.8" \
   -asic_coresize "10.07 11.2 90.25 91" \
   -asic_floorplan examples/counter/counter_floorplan.py \
   -loglevel "INFO" \
   -design counter \
   -quiet
