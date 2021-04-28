#!/bin/bash
mkdir -p ./build/gcd
GCD_DIR=`dirname "$0"`

sc $GCD_DIR/gcd.v \
  -design gcd \
  -target freepdk45 \
  -asic_diesize "0 0 100.13 100.8" \
  -asic_coresize "10.07 11.2 90.25 91" \
  -constraint $GCD_DIR/constraint.sdc \
  -permutations $GCD_DIR/2jobs.py

if [[ -f "./build/gcd/job1/export/outputs/gcd.gds" ]] && \
   [[ -f "./build/gcd/job2/export/outputs/gcd.gds" ]]; then
  echo "Success!"
  exit 0
fi
echo "Fail :("
exit 1
