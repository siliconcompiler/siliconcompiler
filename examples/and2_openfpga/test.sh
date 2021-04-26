#!/usr/bin/env bash

sc examples/and2_openfpga/and2.v \
    -target "openfpga_vpr" \
    -design "and2"

if [[ -f "./build/and2/job1/apr/outputs/and2_fabric_bitstream.txt" ]] && \
   [[ -f "./build/and2/job1/apr/outputs/and2_fabric_bitstream.xml" ]] && \
   [[ -f "./build/and2/job1/apr/outputs/and2_fabric_independent_bitstream.xml" ]]
then
  echo "Success!"
  exit 0
fi
echo "Fail :("
exit 1
