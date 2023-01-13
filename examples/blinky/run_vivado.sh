#!/usr/bin/env bash

sc -input "rtl verilog blinky_fusesoc.v" \
   -fpga_partname "xc7a35ticsg324" \
   -target "fpgaflow_demo" \
   -relax \
   -input "fpga xdc blinky_fusesoc.xdc" \
   -design "blinky"
