#!/usr/bin/env bash

sc blinky.v icebreaker.pcf \
   -fpga_partname "ice40up5k-sg48" \
   -target "lattice_ice40_fpga_demo" \
   -design "blinky"
