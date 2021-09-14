#!/usr/bin/env bash

sc examples/blinky/blinky_fusesoc.v \
   -target "xc7a35ticsg324_fpgaflow" \
   -mode "fpga" \
   -relax \
   -constraint "examples/blinky/blinky_fusesoc.xdc" \
   -design "blinky"
