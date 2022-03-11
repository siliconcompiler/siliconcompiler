#!/usr/bin/env bash

sc blinky.v \
    -fpga_partname "ice40up5k-sg48" \
    -target "fpgaflow_demo" \
    -constraint "icebreaker.pcf" \
    -design "blinky"
