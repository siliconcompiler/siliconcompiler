#!/usr/bin/env bash

sc examples/and2_openfpga/and2.v \
    -target "openfpga_vpr"

if [[ -f "./build/apr/job1/outputs/and2_fabric_bitstream.txt" ]] && \
   [[ -f "./build/apr/job1/outputs/and2_fabric_bitstream.xml" ]] && \
   [[ -f "./build/apr/job1/outputs/and2_fabric_independent_bitstream.xml" ]]
then
  echo "Success!"
  exit 0
fi
echo "Fail :("
exit 1
