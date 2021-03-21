#!/bin/sh
sc examples/gcd/gcd.v \
   -target "freepdk45" \
   -diesize "0 0 100.13 100.8" \
   -coresize "10.07 11.2 90.25 91" \
   -stop "place" \
   -goal_setup_tns "syn 0.0" \
   -design gcd -quiet
