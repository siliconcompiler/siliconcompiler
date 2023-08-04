#!/usr/bin/env bash

sc blinky.v icebreaker.pcf \
   -fpga "ice40up5k-sg48" \
   -target "fpgaflow_demo" \
   -design "blinky"
