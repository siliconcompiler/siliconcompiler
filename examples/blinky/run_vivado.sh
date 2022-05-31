#!/usr/bin/env bash

sc -input "verilog blinky_fusesoc.v" \
   -fpga_partname "xc7a35ticsg324" \
   -target "fpgaflow_demo" \
   -relax \
   -input "xdc blinky_fusesoc.xdc" \
   -design "blinky"
