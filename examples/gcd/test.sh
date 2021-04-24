#!/bin/bash
sc ./examples/gcd/gcd.v \
  -design gcd \
  -target freepdk45 \
  -asic_diesize "0 0 100.13 100.8" \
  -asic_coresize "10.07 11.2 90.25 91" \
  -constraint examples/gcd/constraint.sdc

if test -f "./build/export/job1/outputs/gcd.gds"; then
  echo "Success!"
  exit 0
fi
echo "Fail :("
exit 1
