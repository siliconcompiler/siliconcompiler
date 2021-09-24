#!/usr/bin/env bash

sc examples/blinky/blinky_fusesoc.v \
   -target "fpgaflow_xc7a35ticsg324" \
   -mode "fpga" \
   -relax \
   -constraint "examples/blinky/blinky_fusesoc.xdc" \
   -design "blinky"
