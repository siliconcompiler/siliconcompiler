#!/usr/bin/env bash

sc -input "rtl verilog blinky.v" \
   -input "fpga pcf icebreaker.pcf" \
   -fpga_partname "ice40up5k-sg48" \
   -target "fpgaflow_demo" \
   -design "blinky"
