#!/usr/bin/env bash

sc blinky.v icebreaker.pcf \
   -fpga_partname "ice40up5k-sg48" \
   -target "fpgaflow_demo" \
   -design "blinky" \
   -tool_task_var "yosys syn lut_size 4"
