#!/usr/bin/env bash

sc blinky_fusesoc.v \
   -fpga_partname "xc7a35ticsg324" \
   -target "fpgaflow_demo" \
   -relax \
   -constraint "blinky_fusesoc.xdc" \
   -design "blinky"
