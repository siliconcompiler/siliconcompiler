#!/usr/bin/env bash

sc  -input "verilog blinky.v" \
    -fpga_partname "ice40up5k-sg48" \
    -target "fpgaflow_demo" \
    -input "pcf icebreaker.pcf" \
    -design "blinky"
