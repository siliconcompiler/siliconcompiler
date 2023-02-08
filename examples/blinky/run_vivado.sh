#!/usr/bin/env bash

sc blinky_fusesoc.v blinky_fusesoc.xdc \
   -fpga_partname "xc7a35ticsg324" \
   -target "fpgaflow_demo" \
   -relax \
   -design "blinky"
